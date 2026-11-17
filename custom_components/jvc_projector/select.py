"""Select platform for the jvc_projector integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JVCConfigEntry, JvcProjectorDataUpdateCoordinator
from ._vendor.jvcprojector import const
from .entity import JvcProjectorEntity


@dataclass(frozen=True, kw_only=True)
class JvcProjectorSelectDescription(SelectEntityDescription):
    """Describes JVC Projector select entities."""

    models: frozenset[str] | None = None


# these options correspond to a command and its possible values
# note low latency is intentionally excluded because you can't just turn it on you need to meet conditions first so you should instead switch picture modes
OPTIONS: Final[dict[str, list[str]]] = {
    "picture_mode": [
        name
        for code, name in const.VAL_PICTURE_MODE.items()
        if code not in {"1B", "1C", "1D", "1E"}
    ],
    "input": const.VAL_FUNCTION_INPUT,
    "eshift": const.VAL_TOGGLE,
    "installation_mode": const.VAL_INSTALLATION_MODE,
    "anamorphic": const.VAL_ANAMORPHIC,
    "laser_power": const.VAL_LASER_POWER,
    "laser_dimming": const.VAL_LASER_DIMMING,
}


# create a select for each option defined
SELECTS: Final[list[JvcProjectorSelectDescription]] = [
    JvcProjectorSelectDescription(
        key=key,
        translation_key=key,
        options=list(options),
    )
    for key, options in OPTIONS.items()
]

MODERN_MODELS = frozenset(const.MODERN_MODELS)

SELECTS.extend(
    JvcProjectorSelectDescription(
        key=key,
        translation_key=key,
        options=list(options),
        models=MODERN_MODELS,
        entity_registry_enabled_default=enabled,
    )
    for key, options, enabled in (
        (const.KEY_ALLM, const.VAL_TOGGLE, True),
        (const.KEY_DEEP_BLACK, const.VAL_TOGGLE, True),
        (const.KEY_FILMMAKER_AUTO, ["manual", "auto"], False),
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: JVCConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the JVC Projector platform from a config entry."""
    coordinator = entry.runtime_data

    async_add_entities(
        JvcProjectorSelectEntity(coordinator, description)
        for description in SELECTS
        if description.models is None or coordinator.device.model in description.models
    )


class JvcProjectorSelectEntity(JvcProjectorEntity, SelectEntity):
    """Representation of a JVC Projector select entity."""

    entity_description: JvcProjectorSelectDescription

    def __init__(
        self,
        coordinator: JvcProjectorDataUpdateCoordinator,
        description: JvcProjectorSelectDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, context=description.key)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"
        if self.device.model in MODERN_MODELS:
            raw_command = const.KEY_MAP_TO_COMMAND[description.key]
            if values := const.MODERN_COMMAND_VALUES.get(raw_command):
                self._attr_options = list(values.values())

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return self.coordinator.data.get(self.entity_description.key)

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self.coordinator.async_execute_command(
            lambda: self.device.send_command(self.entity_description.key, option)
        )
        await self.coordinator.async_request_refresh()
