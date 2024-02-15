"""Implement JVC component."""
from collections.abc import Iterable
import logging
import asyncio
from dataclasses import asdict

from jvc_projector.jvc_projector import JVCInput, JVCProjectorCoordinator
import voluptuous as vol

from homeassistant.components.remote import PLATFORM_SCHEMA, RemoteEntity
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_TIMEOUT,
    CONF_SCAN_INTERVAL,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
        vol.Required(CONF_SCAN_INTERVAL): cv.time_period,
        vol.Optional(CONF_TIMEOUT): cv.positive_int,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType = None,
) -> None:
    """Set up platform."""
    options = JVCInput(config.get(CONF_HOST), config.get(CONF_PASSWORD), 20554, int(config.get(CONF_TIMEOUT, 3)))
    name = config.get(CONF_NAME)
    jvc_client = JVCProjectorCoordinator(
        options,
        logger=_LOGGER,
    )
    # create a long lived connection
    jvc_client.open_connection()
    async_add_entities(
        [
            JVCRemote(name, options, jvc_client),
        ]
    )


class JVCRemote(RemoteEntity):
    """Implements the interface for JVC Remote in HA."""

    def __init__(
        self,
        name: str,
        options: JVCInput,
        jvc_client: JVCProjectorCoordinator = None,
    ) -> None:
        """JVC Init."""
        self._name = name
        self._host = options.host

        self.jvc_client = jvc_client
        # TODO: dataclass
        # attributes
        self._state = False
        self._lowlatency_enabled = ""
        self._installation_mode = ""
        self._picture_mode = ""
        self._input_mode = ""
        self._laser_mode = ""
        self._eshift = ""
        self._color_mode = ""
        self._input_level = ""
        self._content_type = ""
        self._content_type_trans = ""
        self._hdr_processing = ""
        self._hdr_level = ""
        self._lamp_power = ""
        self._hdr_data = ""
        self._theater_optimizer = ""
        self._laser_power = ""
        self._aspect_ratio = ""
        self._mask_mode = ""
        self._source_status = ""

        self._model_family = self.jvc_client.model_family

        # async queue
        self.tasks = []
        self.command_queue = asyncio.Queue()
        self.dead_letter_queue = asyncio.Queue()
        self.attribute_queue = asyncio.Queue()
        self.stop_processing_commands = asyncio.Event()
        self.lock = asyncio.Lock()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # add the queue handler to the event loop
        queue_handler = self.hass.loop.create_task(self.handle_queue())
        self.tasks.append(queue_handler)
        worker_handler = self.hass.loop.create_task(self.update_worker())
        self.tasks.append(worker_handler)

    async def async_will_remove_from_hass(self) -> None:
        """close the connection and cancel all tasks when the entity is removed"""
        self.jvc_client.close_connection()
        for task in self.tasks:
            if not task.done():
                task.cancel()

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
            ):
                command: Iterable[str] = await self.command_queue.get()
                _LOGGER.debug("sending queue command %s", command)
                await self.process_command(command)
                await asyncio.sleep(0.1)
                # process the dead letter queue
                await self.process_dlq()
            # if we are stopping and the queue is not empty, clear it
            # this is so it doesnt continuously print the stopped processing commands message
            if self.stop_processing_commands.is_set() and not self.command_queue.empty():
                await self.clear_queue()
                _LOGGER.debug("Stopped processing commands")
                # break to the outer loop so it can restart itself if needed
                break
            # save cpu
            await asyncio.sleep(0.1)

    async def clear_queue(self):
        """Clear the queue"""
        while not self.command_queue.empty():
            await self.command_queue.get()
            self.command_queue.task_done()

    async def process_dlq(self):
        """Process the dead letter queue"""
        if not self.dead_letter_queue.empty():
            command: Iterable[str] = await self.dead_letter_queue.get()
            try:
                # lock the command
                await self.lock.acquire()
                await self.jvc_client.exec_command(command)
                _LOGGER.debug("Command executed successfully from DLQ: %s", command)
                return  # Exit the retry loop upon success
            except Exception as err: # pylint: disable=broad-except
                _LOGGER.error("DLQ attempt failed for %s: %s", command, err)
                return
            finally:
                self.lock.release()

    async def process_command(self, command):
        """async process a command"""
        max_retries = 3
        retry_delay = 1

        # Retry the command a few times before adding to DLQasync_update
        for attempt in range(max_retries):
            try:
                await self.lock.acquire()
                await self.jvc_client.exec_command(command)
                _LOGGER.info("Command executed successfully: %s", command)
                break  # Exit the retry loop upon success
            # intentionally catching all exceptions for dlq
            except Exception as err: # pylint: disable=broad-except
                _LOGGER.error("Attempt %s failed for command %s: %s", attempt + 1, command, err)
                if attempt <= max_retries - 1:
                    await asyncio.sleep(retry_delay)  # Wait before retrying
                else:
                    _LOGGER.error("Sending command to be retried later %s", command)
                    # add the failed command to the DLQ
                    await self.dead_letter_queue.put(command)
            finally:
                self.lock.release()

        self.command_queue.task_done()

    @property
    def should_poll(self):
        """Poll."""
        return True

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
            return asdict(self.jvc_client.attributes)

        return {
            "power_state": self._state
        }

    @property
    def is_on(self):
        """Return the last known state of the projector."""

        return self._state

    async def async_turn_on(self, **kwargs): # pylint: disable=unused-argument
        """Send the power on command."""

        await self.jvc_client.power_on()
        await self.stop_processing_commands.clear()
        self._state = True

    async def async_turn_off(self, **kwargs): # pylint: disable=unused-argument
        """Send the power off command."""

        await self.jvc_client.power_off()
        await self.stop_processing_commands.set()
        self._state = False

    async def update_worker(self):
        """Gets a function and attribute from a queue and runs it."""
        while True:
            if not self.stop_processing_commands.is_set():
                # getter will be a function like get_source_status()
                getter, attribute = await self.attribute_queue.get()
                try:
                    # get lock
                    await self.lock.acquire()
                    value = await getter()
                    setattr(self.jvc_client.attributes, attribute, value)
                # TODO: less broad
                except Exception as err: # pylint: disable=broad-except
                    _LOGGER.error("Error getting attribute: %s", err)
                finally:
                    self.attribute_queue.task_done()
                    self.lock.release()
            await asyncio.sleep(0.1)

    async def async_update(self):
        """Retrieve latest state."""
        if not self.stop_processing_commands.is_set():
            # common stuff
            attribute_getters = [
                (self.jvc_client.is_on, "power_state"),
                (self.jvc_client.get_source_status, "signal_status"),
                (self.jvc_client.get_picture_mode, "picture_mode"),
                (self.jvc_client.get_lamp_time, "lamp_time"),
                (self.jvc_client.get_software_version, "software_version"),
            ]
            # get power, signal and picture state
            for getter, name in attribute_getters:
                await self.attribute_queue.put((getter, name))

            # wait for queue to empty
            await self.attribute_queue.join()

            # determine how to proceed based on above

            if self.jvc_client.attributes.signal_status == "signal":
                attribute_getters.append(
                    (self.jvc_client.get_content_type, "content_type"),
                    (self.jvc_client.get_content_type_trans, "content_type_trans"),
                    (self.jvc_client.get_input_mode, "input_mode"),
                )
            if not "Unsupported" in self.jvc_client.model_family:
                attribute_getters.append(
                    (self.jvc_client.get_install_mode, "installation_mode"),
                    (self.jvc_client.get_aspect_ratio, "aspect_ratio"),
                    (self.jvc_client.get_color_mode, "color_mode"),
                    (self.jvc_client.get_input_level, "input_level"),
                    (self.jvc_client.get_mask_mode, "mask_mode"),
                )
            if any(x in self.jvc_client.model_family for x in ["NX9", "NZ"]):
                attribute_getters.append(
                    (self.jvc_client.get_eshift_mode, "eshift"),
                )
            if "NZ" in self.jvc_client.model_family:
                attribute_getters.append(
                    (self.jvc_client.get_laser_power, "laser_power"),
                    (self.jvc_client.get_laser_mode, "laser_mode"),
                    (self.jvc_client.is_ll_on, "low_latency"),
                )
            else:
                attribute_getters.append(
                    (self.jvc_client.get_lamp_power, "lamp_power"),
                )
            # HDR stuff
            if any(x in self._content_type_trans for x in ["hdr", "hlg"]):
                if "NZ" in self._model_family:
                    attribute_getters.append(
                        (self.jvc_client.get_theater_optimizer_state, "theater_optimizer"),
                    )
                # TODO: each one can time out separately
                attribute_getters.append(
                    (self.jvc_client.get_hdr_processing, "hdr_processing"),
                    (self.jvc_client.get_hdr_level, "hdr_level"),
                    (self.jvc_client.get_hdr_data, "hdr_data"),
                )

            # get all the updates
            for getter, name in attribute_getters:
                await self.attribute_queue.put((getter, name))

            await self.attribute_queue.join()
            
            # set the model
            self.jvc_client.attributes.model = self.jvc_client.model_family
            # just in case
            self._state = self.jvc_client.attributes.power_state
            # Common attributes
            # self._lowlatency_enabled = self.jvc_client.is_ll_on()
            # self._picture_mode = self.jvc_client.get_picture_mode()
            # self._input_mode = self.jvc_client.get_input_mode()

            # # some older models don't support these
            # if not "Unsupported" in self._model_family:
            #     self._installation_mode = self.jvc_client.get_install_mode()
            #     self._aspect_ratio = self.jvc_client.get_aspect_ratio()
            #     self._color_mode = self.jvc_client.get_color_mode()
            #     self._input_level = self.jvc_client.get_input_level()
            #     self._mask_mode = self.jvc_client.get_mask_mode()
            #     self._source_status = self.jvc_client.get_source_status()
            # # TODO: lamp time
            # # TODO: get_software_version
            # if self._source_status == "signal":
            #     try:
            #         # latest firmware of NX also has content type
            #         self._content_type = self.jvc_client.get_content_type()
            #         self._content_type_trans = (
            #             self.jvc_client.get_content_type_trans()
            #         )
            #     except TimeoutError:
            #         _LOGGER.error("timeout getting content type")

            # # Eshift for NX9 and NZ only
            # if any(x in self._model_family for x in ["NX9", "NZ"]):
            #     self._eshift = self.jvc_client.get_eshift_mode()

            # # laser power
            # if "NZ" in self._model_family:
            #     self._laser_mode = self.jvc_client.get_laser_mode()
            #     self._laser_power = self.jvc_client.get_laser_power()
            # else:
            #     self._lamp_power = self.jvc_client.get_lamp_power()

            # # get HDR data
            # if any(x in self._content_type_trans for x in ["hdr", "hlg"]):
            #     try:
            #         if "NZ" in self._model_family:
            #             self._theater_optimizer = (
            #                 self.jvc_client.get_theater_optimizer_state()
            #             )
            #     except TimeoutError:
            #         _LOGGER.error("timeout getting theater optimzer data")
            #     try:
            #         # both nx and nz support these
            #         self._hdr_processing = self.jvc_client.get_hdr_processing()
            #     except TimeoutError:
            #         _LOGGER.error("timeout getting HDR processing")
            #     try:
            #         self._hdr_level = self.jvc_client.get_hdr_level()
            #     except TimeoutError:
            #         _LOGGER.error("timeout getting HDR level")
            #     try:
            #         self._hdr_data = self.jvc_client.get_hdr_data()
            #     except TimeoutError:
            #         _LOGGER.error("timeout getting HDR data")

    async def async_send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        _LOGGER.debug("adding command %s to queue", command)
        await self.command_queue.put(command)
        # retry = 0
        # _LOGGER.debug("adding command %s", command)
        # while retry < 10:
        #     # don't send command until update is done
        #     if self._is_updating is True:
        #         time.sleep(1)
        #         retry += 1
        #         continue
        #     # TODO: add to queue
        #     # set cmd running flag, run cmd, then break
        #     self._command_running = True
        #     await self.jvc_client.exec_command(command)
        #     self._command_running = False
        #     break
