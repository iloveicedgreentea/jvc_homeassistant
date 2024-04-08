"""Implement JVC component."""

from collections.abc import Iterable
import logging
import asyncio
from dataclasses import asdict
import datetime
import itertools

from jvc_projector.jvc_projector import JVCInput, JVCProjectorCoordinator, Header
from jvc_projector.error_classes import ShouldReconnectError
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN

from homeassistant.components.remote import RemoteEntity
from homeassistant.const import (
    CONF_NAME,
)
from homeassistant.core import HomeAssistant

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s - Line: %(lineno)d",
)
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
        self.jvc_client.logger = _LOGGER
        # attributes
        self._state = False

        # async queue
        self.tasks = []
        # use one queue for all commands
        self.command_queue = asyncio.PriorityQueue()
        self.attribute_queue = asyncio.Queue()

        self.stop_processing_commands = asyncio.Event()

        self.hass = hass
        self._update_interval = None

        # counter for unique IDs
        self._counter = itertools.count()

        self.attribute_getters = set()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # add the queue handler to the event loop
        # get updates in a set interval
        self._update_interval = async_track_time_interval(
            self.hass, self.async_update_state, datetime.timedelta(seconds=5)
        )
        # open connection
        conn = self.hass.loop.create_task(self.open_conn())
        self.tasks.append(conn)

        # handle commands
        queue_handler = self.hass.loop.create_task(self.handle_queue())
        self.tasks.append(queue_handler)

        # handle updates
        update_worker = self.hass.loop.create_task(self.update_worker())
        self.tasks.append(update_worker)

        # handle sending attributes to queue
        update_handler = self.hass.loop.create_task(self.make_updates())
        self.tasks.append(update_handler)

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

    async def open_conn(self):
        """Open the connection to the projector."""
        _LOGGER.debug("About to open connection with jvc_client: %s", self.jvc_client)
        try:
            _LOGGER.debug("Opening connection to %s", self.host)
            res = await asyncio.wait_for(self.jvc_client.open_connection(), timeout=3)
            if res:
                _LOGGER.debug("Connection to %s opened", self.host)
                return True
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout while trying to connect to %s", self._host)
        except asyncio.CancelledError:
            return
        # intentionally broad
        except TypeError as err:
            # this is benign, just means the PJ is not connected yet
            _LOGGER.debug("open_connection: %s", err)
            return
        except Exception as err:
            await self.reset_everything()
            _LOGGER.error("some error happened with open_connection: %s", err)
        await asyncio.sleep(5)

    async def generate_unique_id(self) -> int:
        """this is used to sort the queue because it contains non-comparable items"""
        return next(self._counter)

    async def wait_until_connected(self, wait_time: float = 0.1) -> bool:
        """Wait until the connection is open."""
        while not self.jvc_client.connection_open:
            await asyncio.sleep(wait_time)
        return True

    async def handle_queue(self):
        """
        Handle items in command queue.
        This is run in an event loop
        """
        while True:
            await self.wait_until_connected(5)
            try:
                _LOGGER.debug(
                    "queue size is %s - attribute size is %s",
                    self.command_queue.qsize(),
                    self.attribute_queue.qsize(),
                )
                # send all commands in queue
                # can be a command or a tuple[function, attribute]
                # first item is the priority
                try:
                    priority, item = await asyncio.wait_for(
                        self.command_queue.get(), timeout=5
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug("Timeout in command queue")
                    continue
                _LOGGER.debug("got queue item %s with priority %s", item, priority)
                # if its a 3 its an attribute tuple
                if len(item) == 3:
                    # discard the unique ID
                    _, getter, attribute = item
                    _LOGGER.debug(
                        "trying attribute %s with getter %s", attribute, getter
                    )
                    try:
                        await asyncio.sleep(
                            0.2
                        )  # PJ seems to freeze if you send too many commands
                        value = await asyncio.wait_for(getter(), timeout=3)
                    except asyncio.TimeoutError:
                        _LOGGER.debug("Timeout with item %s", item)
                        try:
                            # if the above command times out, but we wrote to buffer, that means there is unread data in response
                            # this needs to clear the buffer if timeout
                            await self.jvc_client.reset_everything()
                            self.command_queue.task_done()
                        except ValueError:
                            pass
                        continue
                    _LOGGER.debug("got value %s for attribute %s", value, attribute)
                    setattr(self.jvc_client.attributes, attribute, value)
                    self.async_write_ha_state()
                elif len(item) == 2:
                    # run the item and set type to operation
                    # HA sends commands like ["power, on"] which is one item
                    _, command = item
                    _LOGGER.debug("executing command %s", command)
                    try:
                        await asyncio.wait_for(
                            self.jvc_client.exec_command(
                                command, Header.operation.value
                            ),
                            timeout=5,
                        )
                    except asyncio.TimeoutError:
                        _LOGGER.debug("Timeout with command %s", command)
                        try:
                            self.command_queue.task_done()
                        except ValueError:
                            pass
                        continue
                    except ShouldReconnectError:
                        _LOGGER.error("Lost connection, reconnecting")
                        await self.reset_everything()
                        continue
                try:
                    self.command_queue.task_done()
                except ValueError:
                    pass
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
            except asyncio.CancelledError:
                _LOGGER.debug("handle_queue cancelled")
                return
            except TypeError as err:
                _LOGGER.debug(
                    "TypeError in handle_queue, moving on: %s -- %s", err, item
                )
                # in this case likely the queue priority is the same, lets just skip it
                self.command_queue.task_done()
                continue
            # catch wrong values
            except ValueError as err:
                _LOGGER.error("ValueError in handle_queue: %s", err)
                # Not sure what causes these but we can at least try to ignore them
                self.command_queue.task_done()
                continue
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error("Unhandled exception in handle_queue: %s", err)
                await self.reset_everything()
                continue

    async def reset_everything(self) -> None:
        """resets EVERYTHING. Something with home assistant just doesnt play nice here"""

        _LOGGER.debug("RESETTING - clearing everything")

        try:
            self.stop_processing_commands.set()
            await self.clear_queue()
            await self.jvc_client.reset_everything()
        except Exception as err:
            _LOGGER.error("Error reseting: %s", err)
        finally:
            self.stop_processing_commands.clear()

    async def clear_queue(self):
        """Clear the queue"""
        try:
            # clear the queue
            _LOGGER.debug("Clearing command queue")
            while not self.command_queue.empty():
                self.command_queue.get_nowait()
                self.command_queue.task_done()

            _LOGGER.debug("Clearing attr queue")
            while not self.attribute_queue.empty():
                self.attribute_queue.get_nowait()
                self.attribute_queue.task_done()

            # reset the counter
            _LOGGER.debug("resetting counter")
            self._counter = itertools.count()

        except ValueError:
            pass

    async def update_worker(self):
        """Gets a function and attribute from a queue and adds it to the command interface"""
        while True:
            # this is just an async interface so the other processor doesnt become complicated

            # getter will be a Callable
            try:
                # queue backpressure
                if self.command_queue.qsize() > 10:
                    # this allows the queue to process stuff without filling up
                    _LOGGER.debug("Queue is full, waiting to add attributes")
                    await asyncio.sleep(2)
                    continue
                unique_id, getter, attribute = await self.attribute_queue.get()
                # add to the command queue with a single interface
                await self.command_queue.put((1, (unique_id, getter, attribute)))
                try:
                    self.attribute_queue.task_done()
                except ValueError:
                    pass
            except asyncio.TimeoutError:
                _LOGGER.debug("Timeout in update_worker")
            except asyncio.CancelledError:
                _LOGGER.debug("update_worker cancelled")
                return
            await asyncio.sleep(0.1)

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
        await self.wait_until_connected()
        try:
            await self.jvc_client.power_on()
            self.stop_processing_commands.clear()
            # save state
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error turning on projector: %s", err)
            await self.reset_everything()
            self._state = False
        finally:
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):  # pylint: disable=unused-argument
        """Send the power off command."""
        await self.wait_until_connected()
        self._state = False

        try:
            await self.jvc_client.power_off()
            self.stop_processing_commands.set()
            await self.clear_queue()
            # save state
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error("Error turning off projector: %s", err)
            await self.reset_everything()
            self._state = False
        finally:
            self.async_write_ha_state()

    async def make_updates(self):
        """
        Runs as a background task
        Add all the attribute getters to the queue.
        """
        while True:
            # copy it so we can remove items from it
            attrs = self.attribute_getters.copy()
            # dedupe by name
            dedupe = set()
            for getter, name in attrs:
                if name not in dedupe:
                    # you might be thinking why is this here?
                    # oh boy let me tell you
                    # TLDR priority queues need a unique ID to sort and you need to just dump one in
                    # otherwise you get a TypeError that home assistant HIDES from you and you spend a week figuring out
                    # why this function deadlocks for no reason, and that HA hides error raises
                    # because the underlying items are not sortable
                    unique_id = await self.generate_unique_id()
                    await self.attribute_queue.put((unique_id, getter, name))
                    # add that we processed it
                    dedupe.add(name)

                    # remove the added item from the shared set
                    self.attribute_getters.discard((getter, name))

            await asyncio.sleep(0.1)

    async def async_update_state(self, _):
        """
        Retrieve latest state.
        This will push the attributes to the queue and be processed by make_updates
        """
        if await self.wait_until_connected():
            # certain commands can only run at certain times
            # if they fail (i.e grayed out on menu) JVC will simply time out. Bad UX
            # have to add specific commands in a precise order
            # get power
            self.attribute_getters.add((self.jvc_client.is_on, "power_state"))

            self._state = self.jvc_client.attributes.power_state
            _LOGGER.debug("power state is : %s", self._state)

            if self._state:
                # takes a func and an attribute to write result into
                self.attribute_getters.update(
                    [
                        (self.jvc_client.get_source_status, "signal_status"),
                        (self.jvc_client.get_picture_mode, "picture_mode"),
                        (self.jvc_client.get_software_version, "software_version"),
                    ]
                )
                if self.jvc_client.attributes.signal_status is True:
                    self.attribute_getters.update(
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
                if "Unsupported" not in self.jvc_client.model_family:
                    self.attribute_getters.update(
                        [
                            (self.jvc_client.get_install_mode, "installation_mode"),
                            (self.jvc_client.get_aspect_ratio, "aspect_ratio"),
                            (self.jvc_client.get_color_mode, "color_mode"),
                            (self.jvc_client.get_input_level, "input_level"),
                            (self.jvc_client.get_mask_mode, "mask_mode"),
                        ]
                    )
                if any(x in self.jvc_client.model_family for x in ["NX9", "NZ"]):
                    self.attribute_getters.add(
                        (self.jvc_client.get_eshift_mode, "eshift"),
                    )
                if "NZ" in self.jvc_client.model_family:
                    self.attribute_getters.update(
                        [
                            (self.jvc_client.get_laser_power, "laser_power"),
                            (self.jvc_client.get_laser_mode, "laser_mode"),
                            (self.jvc_client.is_ll_on, "low_latency"),
                            (self.jvc_client.get_lamp_time, "laser_time"),
                        ]
                    )
                else:
                    self.attribute_getters.update(
                        [
                            (self.jvc_client.get_lamp_power, "lamp_power"),
                            (self.jvc_client.get_lamp_time, "lamp_time"),
                        ]
                    )

                # get laser value if fw is a least 3.0
                if "NZ" in self.jvc_client.model_family:
                    try:
                        if float(self.jvc_client.attributes.software_version) >= 3.00:
                            self.attribute_getters.update(
                                [
                                    (self.jvc_client.get_laser_value, "laser_value"),
                                ]
                            )
                    except ValueError:
                        pass
                # HDR stuff
                if any(
                    x in self.jvc_client.attributes.content_type_trans
                    for x in ["hdr", "hlg"]
                ):
                    if "NZ" in self.jvc_client.model_family:
                        self.attribute_getters.add(
                            (
                                self.jvc_client.get_theater_optimizer_state,
                                "theater_optimizer",
                            ),
                        )
                    self.attribute_getters.update(
                        [
                            (self.jvc_client.get_hdr_processing, "hdr_processing"),
                            (self.jvc_client.get_hdr_level, "hdr_level"),
                            (self.jvc_client.get_hdr_data, "hdr_data"),
                        ]
                    )

            # set the model and power
            self.jvc_client.attributes.model = self.jvc_client.model_family
            self.async_write_ha_state()

    async def async_send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        # add counter to preserve cmd order
        unique_id = await self.generate_unique_id()
        await self.command_queue.put((0, (unique_id, command)))
        _LOGGER.debug("command %s added to queue with counter %s", command, unique_id)


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
