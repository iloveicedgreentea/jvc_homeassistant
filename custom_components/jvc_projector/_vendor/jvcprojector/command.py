"""Module for representing a JVC Projector command."""

from __future__ import annotations

from collections.abc import Callable
import logging
import re
from typing import Final, Any
import math
from . import const

_LOGGER = logging.getLogger(__name__)

PJOK: Final = b"PJ_OK"
PJNG: Final = b"PJ_NG"
PJREQ: Final = b"PJREQ"
PJACK: Final = b"PJACK"
PJNAK: Final = b"PJNAK"

UNIT_ID: Final = b"\x89\x01"
HEAD_OP: Final = b"!" + UNIT_ID
HEAD_REF: Final = b"?" + UNIT_ID
HEAD_RES: Final = b"@" + UNIT_ID
HEAD_ACK: Final = b"\x06" + UNIT_ID
HEAD_LEN: Final = 1 + len(UNIT_ID)
END: Final = b"\n"

TEST: Final = "\0\0"

AUTH_SALT: Final = "JVCKWPJ"


class JvcCommand:
    """Class for representing a JVC Projector command."""

    def __init__(self, code: str, is_ref=False, *, model: str | None = None):
        """Initialize class."""
        self.code = code
        self.is_ref = is_ref
        self.model = model
        self.ack = False
        self._response: str | None = None

    @property
    def response(self) -> str | None:
        """Return command response."""
        if not self.is_ref or self._response is None:
            return None

        if (
            self.model in const.MODERN_MODELS
            and self.code in const.MODERN_COMMAND_VALUES
        ):
            return const.MODERN_COMMAND_VALUES[self.code].get(
                self._response, self._response
            )

        res = self.code + self._response
        val: str = res[len(self.code) :]

        for pat, fmt in self.formatters.items():
            m = re.search(r"^" + pat + r"$", res)
            if m:
                if isinstance(fmt, list):
                    try:
                        index = int(m[1], 16)
                        if 0 <= index < len(fmt):
                            return fmt[index]
                        return val  # noqa: TRY300
                    except ValueError:
                        msg = "response '%s' not int for cmd '%s'"
                        _LOGGER.warning(msg, val, self.code)
                elif isinstance(fmt, dict):
                    try:
                        return fmt[m[1]]
                    except KeyError:
                        msg = "response '%s' not mapped for cmd '%s'"
                        _LOGGER.warning(msg, val, self.code)
                elif callable(fmt):
                    try:
                        return fmt(m)
                    except Exception as e:  # noqa: BLE001
                        msg = "response format failed with %s for '%s (%s)'"
                        _LOGGER.warning(msg, e, self.code, val)
                break

        return val

    @response.setter
    def response(self, data: str) -> None:
        """Set command response."""
        self._response = data

    @property
    def is_power(self) -> bool:
        """Return if command is a power command."""
        return self.code.startswith("PW")

    @staticmethod
    def _build_command_map(
        formatters: dict[str, list | dict | Callable],
    ) -> dict[str, dict[str, Any]]:
        """Use the Formatters object in JvcCommand to build a command map to reduce code duplication."""
        command_map: dict[str, dict[str, Any]] = {}
        for pattern, formatter in formatters.items():
            opcode = pattern.split("(")[0]  # Extract opcode from the f-string
            if isinstance(formatter, dict):
                command_map[opcode] = {
                    "values": formatter,
                    "inverse": {v: k for k, v in formatter.items()},
                }
            elif isinstance(formatter, list):
                command_map[opcode] = {
                    "values": {
                        f"{i:X}": val
                        for i, val in enumerate(formatter)
                        if val is not None
                    },
                    "inverse": {
                        val: f"{i:X}"
                        for i, val in enumerate(formatter)
                        if val is not None
                    },
                }
            elif callable(formatter):
                # A response decoder does not describe a writable range.
                command_map[opcode] = {"values": "callable"}
            else:
                command_map[opcode] = {"values": formatter}
        return command_map

    formatters: dict[str, list | dict | Callable] = {
        f"{const.CMD_POWER}(.)": const.VAL_POWER,
        f"{const.CMD_INPUT}(.)": const.VAL_INPUT,
        f"{const.CMD_SOURCE}(.)": const.VAL_SOURCE,
        f"{const.CMD_MODEL}(.+)": lambda r: re.sub(r"-+", "-", r[1].replace(" ", "-")),
        f"{const.CMD_PICTURE_MODE}(..)": const.VAL_PICTURE_MODE,
        f"{const.CMD_PICTURE_MODE_INTELLIGENT_APERTURE}(.)": const.VAL_INTELLIGENT_APERTURE,
        f"{const.CMD_LASER_DIMMING}(.)": const.VAL_LASER_DIMMING,
        f"{const.CMD_PICTURE_MODE_COLOR_PROFILE}(..)": const.VAL_COLOR_PROFILE,
        f"{const.CMD_PICTURE_MODE_COLOR_TEMP}(..)": const.VAL_COLOR_TEMP,
        f"{const.CMD_PICTURE_MODE_COLOR_CORRECTION}(..)": const.VAL_COLOR_CORRECTION,
        f"{const.CMD_PICTURE_MODE_GAMMA_TABLE}(..)": const.VAL_GAMMA_TABLE,
        f"{const.CMD_PICTURE_MODE_COLOR_MANAGEMENT}(.)": const.VAL_TOGGLE,
        f"{const.CMD_PICTURE_MODE_LOW_LATENCY}(.)": const.VAL_TOGGLE,
        f"{const.CMD_PICTURE_MODE_8K_ESHIFT}(.)": const.VAL_TOGGLE,
        f"{const.CMD_PICTURE_MODE_CLEAR_MOTION_DRIVE}(.)": const.VAL_CLEAR_MOTION_DRIVE,
        f"{const.CMD_PICTURE_MODE_LASER_VALUE}(.+)": lambda r: math.floor(
            ((int(r[1], 16) - 109) / 1.1) + 0.5
        ),
        f"{const.CMD_PICTURE_MODE_MOTION_ENHANCE}(.)": const.VAL_MOTION_ENHANCE,
        f"{const.CMD_PICTURE_MODE_LASER_POWER}(.)": const.VAL_LASER_POWER,
        f"{const.CMD_PICTURE_MODE_GRAPHICS_MODE}(.)": const.VAL_GRAPHICS_MODE,
        f"{const.CMD_INPUT_SIGNAL_HDMI_INPUT_LEVEL}(.)": const.VAL_HDMI_INPUT_LEVEL,
        f"{const.CMD_INPUT_SIGNAL_HDMI_COLOR_SPACE}(.)": const.VAL_HDMI_COLOR_SPACE,
        f"{const.CMD_INPUT_SIGNAL_HDMI_2D_3D}(.)": const.VAL_HDMI_2D_3D,
        f"{const.CMD_INPUT_SIGNAL_ASPECT}(.)": const.VAL_ASPECT,
        f"{const.CMD_INPUT_SIGNAL_MASK}(.)": const.VAL_MASK,
        f"{const.CMD_INSTALLATION_MODE}(.)": const.VAL_INSTALLATION_MODE,
        f"{const.CMD_INSTALLATION_LENS_IMAGE_PATTERN}(.)": const.VAL_TOGGLE,
        f"{const.CMD_INSTALLATION_LENS_LOCK}(.)": const.VAL_TOGGLE,
        f"{const.CMD_INSTALLATION_SCREEN_ADJUST}(.)": const.VAL_TOGGLE,
        f"{const.CMD_INSTALLATION_STYLE}(.)": const.VAL_INSTALLATION_STYLE,
        f"{const.CMD_INSTALLATION_ANAMORPHIC}(.)": const.VAL_ANAMORPHIC,
        f"{const.CMD_DISPLAY_BACK_COLOR}(.)": const.VAL_BACK_COLOR,
        f"{const.CMD_DISPLAY_MENU_POSITION}(.)": const.VAL_MENU_POSITION,
        f"{const.CMD_DISPLAY_SOURCE_DISPLAY}(.)": const.VAL_TOGGLE,
        f"{const.CMD_DISPLAY_LOGO}(.)": const.VAL_TOGGLE,
        f"{const.CMD_FUNCTION_TRIGGER}(.)": const.VAL_TRIGGER,
        f"{const.CMD_FUNCTION_OFF_TIMER}(.)": const.VAL_OFF_TIMER,
        f"{const.CMD_FUNCTION_ECO_MODE}(.)": const.VAL_TOGGLE,
        f"{const.CMD_FUNCTION_CONTROL4}(.)": const.VAL_TOGGLE,
        f"{const.CMD_FUNCTION_INPUT}(.)": const.VAL_FUNCTION_INPUT,
        f"{const.CMD_FUNCTION_SOURCE}(..)": const.VAL_FUNCTION_SOURCE,
        f"{const.CMD_FUNCTION_DEEP_COLOR}(.)": const.VAL_DEEP_COLOR,
        f"{const.CMD_FUNCTION_COLOR_SPACE}(.)": const.VAL_COLOR_SPACE,
        f"{const.CMD_FUNCTION_COLORIMETRY}(.)": const.VAL_COLORIMETRY,
        f"{const.CMD_FUNCTION_HDR}(.)": const.VAL_HDR,
        f"{const.CMD_FUNCTION_LASER_TIME}(.+)": lambda r: int(r[1], 16),
        f"{const.CMD_PICTURE_MODE_HDR_LEVEL}(.)": const.VAL_HDR_LEVEL,
        f"{const.CMD_PICTURE_MODE_HDR_PROCESSING}(.)": const.VAL_HDR_PROCESSING,
        f"{const.CMD_PICTURE_MODE_HDR_CONTENT_TYPE}(.)": const.VAL_HDR_CONTENT_TYPE,
        f"{const.CMD_PICTURE_MODE_THEATER_OPTIMIZER}(.)": const.VAL_TOGGLE,
        f"{const.CMD_PICTURE_MODE_THEATER_OPTIMIZER_LEVEL}(.)": const.VAL_THEATER_OPTIMIZER_LEVEL,
        f"{const.CMD_PICTURE_MODE_THEATER_OPTIMIZER_PROCESSING}(.)": const.VAL_THEATER_OPTIMIZER_PROCESSING,
        f"{const.CMD_PICTURE_MODE_DEEP_BLACK}(.)": const.VAL_TOGGLE,
        f"{const.CMD_PICTURE_MODE_HIGHLIGHT_COLOR}(.)": const.VAL_HIGHLIGHT_COLOR,
        f"{const.CMD_PICTURE_MODE_SMOOTHER}(....)": const.VAL_SMOOTHER,
        f"{const.CMD_INPUT_SIGNAL_ALLM}(.)": const.VAL_TOGGLE,
        f"{const.CMD_INPUT_SIGNAL_FILMMAKER_AUTO}(.)": const.VAL_FILMMAKER_AUTO,
        f"{const.CMD_LAN_SETUP_DHCP}(.)": const.VAL_TOGGLE,
        f"{const.CMD_LAN_SETUP_MAC_ADDRESS}(.+)": lambda r: re.sub(
            r"-+", "-", r[1].replace(" ", "-")
        ),
        f"{const.CMD_LAN_SETUP_IP_ADDRESS}(..)(..)(..)(..)": lambda r: f"{int(r[1], 16)}.{int(r[2], 16)}.{int(r[3], 16)}.{int(r[4], 16)}",
    }

    command_map: dict[str, dict[str, Any]] = _build_command_map(formatters)

    @staticmethod
    def get_available_commands() -> dict[str, str]:
        """Return a map of commands to their allowed values/responses based on the available command_map."""

        human_commands: dict[str, str] = {}
        for cmd, values in JvcCommandHelpers.get_available_commands().items():
            human_commands[cmd] = values["values"]
        return human_commands


class JvcCommandHelpers:
    """Helper methods for JVC Command handling and documentation."""

    # Define override maps for commands where input values differ from return values
    COMMAND_VALUE_OVERRIDES = {
        "power": [
            "on",
            "standby",
        ],  # Can only send standby/on, even though we might receive other states
        "source": None,  # Read-only, can't send values
        "laser_time": None,  # Read-only, can't send values
        "hdr_processing": ["static", "frame", "scene"],  # HDR10+ is reference-only.
        "graphics_mode": [
            "standard",
            "high-res",
            "high-res2",
        ],  # Off is reference-only.
    }

    @staticmethod
    def format_value_name(value: str) -> str:
        """Format a command value into a human-readable string."""
        # Replace underscores with spaces
        formatted = value.replace("_", " ")

        # make sure all words are lowercase
        return " ".join(word.lower() for word in formatted.split())

    @staticmethod
    def format_command_name(command: str) -> str:
        """Format a command name into a human-readable string."""
        # Remove KEY_ prefix if present
        command = re.sub(r"^KEY_", "", command)
        # Replace underscores with spaces
        formatted = command.replace("_", " ")
        # Capitalize first letter of each word
        return " ".join(word.capitalize() for word in formatted.split())

    @staticmethod
    def format_value_list(values: list[str] | dict[str, str]) -> list[str]:
        """Format a list or dict of values into human-readable strings."""
        if isinstance(values, dict):
            # For dictionaries, we only want the values, not the keys
            value_list = list(values.values())
        else:
            value_list = values

        return [JvcCommandHelpers.format_value_name(str(val)) for val in value_list]

    @classmethod
    def get_command_values(
        cls, command: str, values: list[str] | dict[str, str]
    ) -> list[str] | None:
        """Get the appropriate command values, taking into account any overrides.

        Args:
            command: The command key
            values: The default values from the command map

        Returns:
            List of valid input values for the command or None if read-only

        """
        # Check if we have an override for this command
        if command in cls.COMMAND_VALUE_OVERRIDES:
            return cls.COMMAND_VALUE_OVERRIDES[command]

        # No override, process normal values
        return cls.format_value_list(values)

    @classmethod
    def get_available_commands(cls) -> dict[str, dict[str, Any]]:
        """Return a detailed map of commands and their allowed values/responses.

        Returns:
            Dict with structure:
            {
                "command_name": {
                    "name": "Human Readable Name",
                    "values": ["Value 1", "Value 2"],
                    "description": "Command description",
                    "type": "enum|range|read_only",
                    "command": "PJ_COMMAND"  # The raw projector command
                }
            }

        """
        human_commands: dict[str, dict[str, Any]] = {}

        # Command category descriptions
        categories = {
            "POWER": "Controls projector power state",
            "INPUT": "Selects input source",
            "PICTURE_MODE": "Controls picture mode settings",
            "INSTALLATION": "Controls installation and setup options",
            "HDR": "Controls HDR-related settings",
            "LASER": "Controls laser and brightness settings",
            "COLOR": "Controls color-related settings",
            "MOTION": "Controls motion-related settings",
        }

        for human_cmd, pj_cmd in const.KEY_MAP_TO_COMMAND.items():
            command_data = JvcCommand.command_map.get(pj_cmd, {})

            # Skip if no command data found
            if not command_data:
                continue

            # Determine command category
            category = next(
                (cat for cat in categories if cat in human_cmd.upper()),
                "GENERAL",
            )

            values = command_data.get("values", {})

            command_info = {
                "name": cls.format_command_name(human_cmd),
                "category": category,
                "description": categories.get(category, "General setting"),
                "command": pj_cmd,
            }

            # Handle different value types
            if pj_cmd.startswith("IF") or values == "callable":
                command_info["values"] = ""
                command_info["type"] = "read_only"
            elif isinstance(values, (list, dict)):
                command_values = cls.get_command_values(human_cmd, values)
                if command_values is None:
                    command_info["values"] = ""
                    command_info["type"] = "read_only"
                else:
                    # Keep the quoted-string metadata shape for compatibility,
                    # but expose the actual API names (including underscores).
                    allowed = cls.COMMAND_VALUE_OVERRIDES.get(human_cmd)
                    command_info["values"] = ", ".join(
                        f'"{val}"' for val in (allowed or command_data["inverse"])
                    )
                    command_info["type"] = "enum"
            else:
                command_info["values"] = ""
                command_info["type"] = "unknown"

            human_commands[human_cmd] = command_info

        return human_commands

    @classmethod
    def get_command_help(cls, command: str) -> str:
        """Generate a human-readable help string for a specific command.

        Args:
            command: The command key to get help for

        Returns:
            A formatted help string with command details

        """
        commands = cls.get_available_commands()
        if command not in commands:
            return f"Unknown command: {command}"

        cmd_info = commands[command]

        help_text = [
            f"Command: {cmd_info['name']}",
            f"Category: {cmd_info['category']}",
            f"Description: {cmd_info['description']}",
        ]

        if cmd_info["type"] == "read_only":
            help_text.append("Type: Read Only")
        elif cmd_info["type"] == "range":
            help_text.append("Accepts values: 0-100")
        elif cmd_info["values"]:
            help_text.append("Available values:")
            help_text.extend(
                f"  - {value.strip().strip(chr(34))}"
                for value in cmd_info["values"].split(",")
            )

        return "\n".join(help_text)
