"""Sensor platform for JVC Projector integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import JVCConfigEntry, JvcProjectorDataUpdateCoordinator
from ._vendor.jvcprojector import const
from .entity import JvcProjectorEntity

JVC_SENSORS = (
    SensorEntityDescription(
        key=const.KEY_POWER,
        translation_key="jvc_power_status",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_POWER,
    ),
    SensorEntityDescription(
        key=const.KEY_PICTURE_MODE,
        translation_key="jvc_picture_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    SensorEntityDescription(
        key=const.KEY_LASER_VALUE,
        translation_key="jvc_laser_value",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_LASER_TIME,
        translation_key="jvc_laser_time",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_HDR_CONTENT_TYPE,
        translation_key="jvc_hdr_content_type",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_HDR_CONTENT_TYPE,
        entity_registry_enabled_default=False,
    ),
    # niche sensors that are disabled by default
    SensorEntityDescription(
        key=const.KEY_HDR,
        translation_key="jvc_hdr_mode",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_HDR_MODES,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_HDMI_INPUT_LEVEL,
        translation_key="jvc_hdmi_input_level",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_HDMI_INPUT_LEVEL,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_HDMI_COLOR_SPACE,
        translation_key="jvc_hdmi_color_space",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_HDMI_COLOR_SPACE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_COLOR_PROFILE,
        translation_key="jvc_color_profile",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_GRAPHICS_MODE,
        translation_key="jvc_graphics_mode",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_GRAPHICS_MODE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_COLOR_SPACE,
        translation_key="jvc_color_space",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=list(
            dict.fromkeys(
                [*const.VAL_COLOR_SPACE, *const.VAL_COLOR_SPACE_MODERN.values()]
            )
        ),
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_MOTION_ENHANCE,
        translation_key="jvc_motion_enhance",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_MOTION_ENHANCE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_CLEAR_MOTION_DRIVE,
        translation_key="jvc_clear_motion_drive",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_CLEAR_MOTION_DRIVE,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_HDR_PROCESSING,
        translation_key="jvc_hdr_processing_mode",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_HDR_PROCESSING,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_RESOLUTION,
        translation_key="jvc_resolution",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_DEEP_COLOR,
        translation_key="jvc_deep_color",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_DEEP_COLOR,
        entity_registry_enabled_default=False,
    ),
    SensorEntityDescription(
        key=const.KEY_COLORIMETRY,
        translation_key="jvc_colorimetry",
        device_class=SensorDeviceClass.ENUM,
        entity_category=EntityCategory.DIAGNOSTIC,
        options=const.VAL_COLORIMETRY,
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: JVCConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the JVC Projector platform from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        JvcSensor(coordinator, description) for description in JVC_SENSORS
    )


class JvcSensor(JvcProjectorEntity, SensorEntity):
    """The entity class for JVC Projector integration."""

    def __init__(
        self,
        coordinator: JvcProjectorDataUpdateCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the JVC Projector sensor."""
        super().__init__(coordinator, context=description.key)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.unique_id}_{description.key}"

    @property
    def native_value(self) -> str | None:
        """Return the native value."""
        return self.coordinator.data.get(self.entity_description.key)
