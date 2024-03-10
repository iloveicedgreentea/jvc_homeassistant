"""Implement JVC component."""

from collections.abc import Iterable
import logging
import asyncio
from dataclasses import asdict
from typing import Callable
import datetime

from jvc_projector.jvc_projector import JVCInput, JVCProjectorCoordinator, Header
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

from homeassistant.components.remote import RemoteEntity
from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import HomeAssistant

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


class JVCRemote(RemoteEntity):
    """Implements the interface for JVC Remote in HA."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry,
        name: str,
        options: JVCInput,
        jvc_client: JVCProjectorCoordinator = None,
    ) -> None:
        """JVC Init."""
        super().__init__()
        self._name = name
        self._host = options.host
        self.entry = entry
        # tie the entity to the config flow
        self._attr_unique_id = entry.entry_id

        self.jvc_client = jvc_client
        # attributes
        self._state = False

        # async queue
        self.tasks = []
        # use one queue for all commands
        self.command_queue = asyncio.Queue()
        self.attribute_queue = asyncio.Queue()

        self.stop_processing_commands = asyncio.Event()
        self.lock = jvc_client.lock

        self.hass = hass

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # add the queue handler to the event loop
        # get updates in a set interval
        self._update_interval = async_track_time_interval(
            self.hass, self.async_update_state, datetime.timedelta(seconds=5)
        )

        queue_handler = self.hass.loop.create_task(self.handle_queue())
        self.tasks.append(queue_handler)
        ping = self.hass.loop.create_task(self.ping_until_alive())
        self.tasks.append(ping)

    async def async_will_remove_from_hass(self) -> None:
        """close the connection and cancel all tasks when the entity is removed"""
        # close connection
        # stop scheduled updates
        if self._update_interval:
            self._update_interval()
            self._update_interval = None

        await self.jvc_client.close_connection()
        # cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

    async def ping_until_alive(self) -> None:
        """ping unit until its alive if previously connected. Once True, call open_connection. Used when HA was restarted while PJ was on"""

        # if not self._previously_connected:
        #     _LOGGER.debug(
        #         "Projector was not previously connected, skipping reconnection."
        #     )
        #     return
        # TODO: attempt to send a power command to see if its physically on instead of doing state storage
        # TODO: ping  only to see if its available, not to turn it on
        # cmd = f"ping -c 1 -W 2 {self.host}"
        sleep_interval = 5

        while True:
            try:
                _LOGGER.debug("Pinging %s", self.host)
                on = await self.jvc_client.is_on()
                if on:
                    _LOGGER.debug("PJ is on - turning on integration")
                    await self.async_turn_on()
                    return

                if not on and self._state:
                    _LOGGER.debug("PJ is off - turning off integration")
                    await self.async_turn_off()
                    return

                # wait and continue
                await asyncio.sleep(sleep_interval)
                continue

            except asyncio.CancelledError as err:
                _LOGGER.error(err)
                return
            # intentionally broad
            except TypeError as err:
                # this is benign, just means the PJ is not connected yet
                _LOGGER.debug("benign error with ping: %s", err)
                continue
            except Exception as err:
                _LOGGER.error("some error happened with ping: %s", err)
                continue

    async def handle_queue(self):
        """
        Handle items in command queue.
        This is run in an event loop
        """
        while True:
            # send all commands in queue
            while (
                # if the queue is not empty and we are not stopping
                not self.command_queue.empty()
                and not self.stop_processing_commands.is_set()
                and not self.jvc_client.writer is None
                and self.jvc_client.connection_open is True
            ):
                # can be a command or a tuple[function, attribute]
                command: (
                    Iterable[str] | tuple[Callable[[], str | int | bool | float], str]
                ) = await self.command_queue.get()
                _LOGGER.debug("got queue item %s", command)
                # if its a tuple its an attribute update
                if isinstance(command, tuple):
                    getter, attribute = command
                    _LOGGER.debug(
                        "trying attribute %s with getter %s", attribute, getter
                    )
                    value = await getter()
                    _LOGGER.debug("got value %s for attribute %s", value, attribute)
                    setattr(self.jvc_client.attributes, attribute, value)
                else:
                    # run the command and set type to operation
                    # HA sends commands like ["power, on"] which is one item
                    await self.jvc_client.exec_command(command, Header.operation.value)
                await asyncio.sleep(0.1)
            # if we are stopping and the queue is not empty, clear it
            # this is so it doesnt continuously print the stopped processing commands message
            if (
                self.stop_processing_commands.is_set()
                and not self.command_queue.empty()
            ):
                await self.clear_queue()
                _LOGGER.debug("Stopped processing commands")
                # break to the outer loop so it can restart itself if needed
                break
            # save cpu
            await asyncio.sleep(0.1)

    async def clear_queue(self):
        """Clear the queue"""

        # clear the queue
        while not self.command_queue.empty():
            self.command_queue.get_nowait()
            self.command_queue.task_done()

        while not self.attribute_queue.empty():
            self.attribute_queue.get_nowait()
            self.attribute_queue.task_done()

    async def update_worker(self):
        """Gets a function and attribute from a queue and adds it to the command interface"""
        while True:
            if (
                not self.stop_processing_commands.is_set()
                and not self.jvc_client.writer is None
                and self.jvc_client.connection_open is True
            ):
                # this is just an async interface so the other processor doesnt become complicated

                # getter will be a Callable
                getter, attribute = await self.attribute_queue.get()
                # add to the command queue with a single interface
                await self.command_queue.put((getter, attribute))

    @property
    def should_poll(self):
        """Poll."""
        return False

    @property
    def name(self):
        """Name."""
        return self._name

    @property
    def host(self):
        """Host."""
        return self._host

    @property
    def extra_state_attributes(self):
        """Return extra state attributes."""
        # Separate views for models to be cleaner
        if self._state:
            all_attr = asdict(self.jvc_client.attributes)
            # remove lamp stuff if its a laser
            if "NZ" in self.jvc_client.model_family:
                all_attr.pop("lamp_power")
                all_attr.pop("lamp_time")

            return all_attr

        return {
            "power_state": self._state,
            "model": self.jvc_client.model_family,
            "connection_state": self.jvc_client.attributes.connection_active,
        }

    @property
    def is_on(self):
        """Return the last known state of the projector."""
        return self._state

    async def async_turn_on(self, **kwargs):  # pylint: disable=unused-argument
        """Send the power on command."""

        self._state = True

        try:
            await self.jvc_client.power_on()
            self.stop_processing_commands.clear()
            # save state
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error turning on projector: %s", err)
            self._state = False

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Send the power off command."""

        self._state = False

        try:
            await self.jvc_client.power_off()
            self.stop_processing_commands.set()
            await self.clear_queue()
            self.jvc_client.attributes.connection_active = False
            # save state
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error turning off projector: %s", err)
            self._state = False

    async def async_update_state(self, now):
        """Retrieve latest state."""
        if (
            not self.stop_processing_commands.is_set()
            and not self.jvc_client.writer is None
            and self.jvc_client.connection_open is True
        ):
            # certain commands can only run at certain times
            # if they fail (i.e grayed out on menu) JVC will simply time out. Bad UX
            # have to add specific commands in a precise order
            # common stuff
            attribute_getters = []
            _LOGGER.debug("updating state")
            self.jvc_client.attributes.connection_active = (
                self.jvc_client.writer is not None
            )
            self._state = await self.jvc_client.is_on()
            if self._state:
                _LOGGER.debug("getting attributes")
                # takes a func and an attribute to write result into
                attribute_getters.extend(
                    [
                        (self.jvc_client.get_source_status, "signal_status"),
                        (self.jvc_client.get_picture_mode, "picture_mode"),
                        (self.jvc_client.get_software_version, "software_version"),
                    ]
                )
                # determine how to proceed based on above

                if self.jvc_client.attributes.signal_status is True:
                    attribute_getters.extend(
                        [
                            (self.jvc_client.get_content_type, "content_type"),
                            (
                                self.jvc_client.get_content_type_trans,
                                "content_type_trans",
                            ),
                            (self.jvc_client.get_input_mode, "input_mode"),
                            (self.jvc_client.get_anamorphic, "anamorphic_mode"),
                            (self.jvc_client.get_source_display, "resolution"),
                        ]
                    )
                if not "Unsupported" in self.jvc_client.model_family:
                    attribute_getters.extend(
                        [
                            (self.jvc_client.get_install_mode, "installation_mode"),
                            (self.jvc_client.get_aspect_ratio, "aspect_ratio"),
                            (self.jvc_client.get_color_mode, "color_mode"),
                            (self.jvc_client.get_input_level, "input_level"),
                            (self.jvc_client.get_mask_mode, "mask_mode"),
                        ]
                    )
                if any(x in self.jvc_client.model_family for x in ["NX9", "NZ"]):
                    attribute_getters.append(
                        (self.jvc_client.get_eshift_mode, "eshift"),
                    )
                if "NZ" in self.jvc_client.model_family:
                    attribute_getters.extend(
                        [
                            (self.jvc_client.get_laser_power, "laser_power"),
                            (self.jvc_client.get_laser_mode, "laser_mode"),
                            (self.jvc_client.is_ll_on, "low_latency"),
                            (self.jvc_client.get_lamp_time, "laser_time"),
                        ]
                    )
                else:
                    attribute_getters.extend(
                        [
                            (self.jvc_client.get_lamp_power, "lamp_power"),
                            (self.jvc_client.get_lamp_time, "lamp_time"),
                        ]
                    )

                for getter, name in attribute_getters:
                    await self.attribute_queue.put((getter, name))

                # get hdr attributes
                await self.attribute_queue.join()

                # get laser value if fw is a least 3.0
                if "NZ" in self.jvc_client.model_family:
                    if float(self.jvc_client.attributes.software_version) >= 3.00:
                        attribute_getters.extend(
                            [
                                (self.jvc_client.get_laser_value, "laser_value"),
                            ]
                        )
                # HDR stuff
                if any(
                    x in self.jvc_client.attributes.content_type_trans
                    for x in ["hdr", "hlg"]
                ):
                    if "NZ" in self.jvc_client.model_family:
                        attribute_getters.append(
                            (
                                self.jvc_client.get_theater_optimizer_state,
                                "theater_optimizer",
                            ),
                        )
                    attribute_getters.extend(
                        [
                            (self.jvc_client.get_hdr_processing, "hdr_processing"),
                            (self.jvc_client.get_hdr_level, "hdr_level"),
                            (self.jvc_client.get_hdr_data, "hdr_data"),
                        ]
                    )

                # get all the updates
                for getter, name in attribute_getters:
                    await self.attribute_queue.put((getter, name))

                await self.attribute_queue.join()
            else:
                _LOGGER.debug("PJ is off")
            # set the model and power
            self.jvc_client.attributes.model = self.jvc_client.model_family
            self.jvc_client.attributes.power_state = self._state
            self.async_write_ha_state()

    async def async_send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        _LOGGER.debug("adding command %s to queue", command)
        await self.command_queue.put(command)

    # TODO: helper function to add to queue


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    """Set up JVC Remote based on a config entry."""
    # Retrieve your setup data or coordinator from hass.data
    coordinator = hass.data[DOMAIN]

    # You might need to adjust this part based on how your coordinator is structured
    # and how it provides access to device/client information
    name = entry.data.get(CONF_NAME)
    options = (
        coordinator.options
    )  # Assuming your coordinator has an attribute 'options'
    jvc_client = coordinator  # Assuming the coordinator acts as the client

    # Setup your entities and add them
    _LOGGER.debug("Setting up JVC Projector with options: %s", options)
    async_add_entities(
        [JVCRemote(hass, entry, name, options, jvc_client)], update_before_add=False
    )
