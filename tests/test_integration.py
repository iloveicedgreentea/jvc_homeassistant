"""Regression coverage for setup, state, commands and configuration."""

import asyncio
from dataclasses import replace
from unittest.mock import patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jvc_projector._vendor.jvcprojector import const
from custom_components.jvc_projector._vendor.jvcprojector.device import (
    JvcProjectorAuthError,
)
from custom_components.jvc_projector._vendor.jvcprojector.error import (
    JvcProjectorConnectError,
)
from custom_components.jvc_projector.const import DOMAIN
from custom_components.jvc_projector.coordinator import (
    INTERVAL_FAST,
    INTERVAL_SLOW,
    JvcProjectorDataUpdateCoordinator,
)
from custom_components.jvc_projector.remote import JvcProjectorRemote


async def setup_entry(hass, projector):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="JVC Projector",
        unique_id="aa:bb:cc:dd:ee:ff",
        data={CONF_HOST: projector.host, CONF_PORT: 20554},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.jvc_projector.JvcProjector", return_value=projector):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return entry


async def test_real_setup_services_unload_reload(hass: HomeAssistant, projector):
    entry = await setup_entry(hass, projector)
    assert entry.state is ConfigEntryState.LOADED
    # Setup reads identity once; coordinator's idempotent connect has no get_info.
    assert projector.connect.call_args_list[0].args == (True,)
    assert all(not call.args for call in projector.connect.call_args_list[1:])
    registry = er.async_get(hass)
    remote_id = registry.async_get_entity_id("remote", DOMAIN, entry.unique_id)
    assert remote_id
    assert hass.states.get(remote_id).state == "off"
    await hass.services.async_call(
        "remote",
        "send_command",
        {
            "entity_id": remote_id,
            "command": ["up", "remote,down"],
            "num_repeats": 2,
            "delay_secs": 0,
        },
        blocking=True,
    )
    assert [c.args[0] for c in projector.remote.call_args_list] == [
        const.REMOTE_UP,
        const.REMOTE_DOWN,
    ] * 2
    coordinator = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert coordinator._shutdown_requested
    projector.disconnect.assert_awaited()
    with patch("custom_components.jvc_projector.JvcProjector", return_value=projector):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_coordinator_power_polling_auth_recovery(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.STANDBY}
    assert coordinator.update_interval == INTERVAL_SLOW
    projector.get_state.return_value = {const.KEY_POWER: const.ON, "input": None}
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.ON}
    assert coordinator.update_interval == INTERVAL_FAST
    projector.connect.side_effect = JvcProjectorAuthError("wrong password")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
    projector.disconnect.assert_awaited_once()
    projector.connect.side_effect = None
    await coordinator._async_update_data()
    await coordinator.async_shutdown()


async def test_command_failure_not_replayed(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    remote = JvcProjectorRemote(coordinator)
    projector.remote.side_effect = JvcProjectorConnectError("ack lost")
    with pytest.raises(HomeAssistantError):
        await remote.async_send_command(["up"])
    projector.remote.assert_awaited_once()
    projector.disconnect.assert_awaited_once()
    await coordinator.async_shutdown()


@pytest.mark.parametrize(
    "commands,kwargs",
    [
        (["up", "missing"], {}),
        (["up", "input,hdmi"], {}),
        (["power,on"], {"hold_secs": 1}),
        (["up"], {"num_repeats": 0}),
        (["up"], {"num_repeats": 101}),
        (["up"], {"hold_secs": 31}),
        (["up"], {"hold_secs": float("nan")}),
        (["up"], {"delay_secs": float("inf")}),
        (["up"], {"hold_secs": 30, "num_repeats": 100}),
    ],
)
async def test_invalid_batch_has_no_side_effects(hass, projector, commands, kwargs):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    remote = JvcProjectorRemote(coordinator)
    with pytest.raises(ServiceValidationError):
        await remote.async_send_command(commands, **kwargs)
    projector.remote.assert_not_awaited()
    projector.send_command.assert_not_awaited()
    await coordinator.async_shutdown()


async def test_hold_repeats_keys_and_cancellation_stops(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    remote = JvcProjectorRemote(coordinator)
    await remote.async_send_command(["up"], hold_secs=0.35, delay_secs=0.1)
    assert 2 <= projector.remote.await_count <= 4
    task = asyncio.create_task(
        remote.async_send_command(["down"], hold_secs=20, delay_secs=0.1)
    )
    await asyncio.sleep(0.15)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    sent = projector.remote.await_count
    await asyncio.sleep(0.15)
    assert projector.remote.await_count == sent
    await coordinator.async_shutdown()


@pytest.mark.parametrize(
    "kwargs,expected_delay",
    [({}, 0.2), ({"delay_secs": 0.4}, 0.4), ({"delay_secs": 0}, 0.1)],
)
async def test_remote_service_repeat_pacing(hass, projector, kwargs, expected_delay):
    """Default repeats avoid extra delay while explicit pacing stays supported."""
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    remote_id = registry.async_get_entity_id("remote", DOMAIN, entry.unique_id)
    with patch(
        "custom_components.jvc_projector.remote.asyncio.sleep", wraps=asyncio.sleep
    ) as sleep:
        await hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": remote_id, "command": "up", "num_repeats": 2, **kwargs},
            blocking=True,
        )
    assert [call.args[0] for call in sleep.await_args_list] == [expected_delay]
    assert [call.args[0] for call in projector.remote.await_args_list] == [
        const.REMOTE_UP,
        const.REMOTE_UP,
    ]
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_select_refreshes_state(hass, projector):
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    select_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_input"
    )
    assert select_id
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": select_id, "option": "hdmi2"},
        blocking=True,
    )
    projector.send_command.assert_awaited_once_with("input", "hdmi2")
    assert projector.get_state.await_count >= 2
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_config_flow_optional_password(hass, projector):
    with patch(
        "custom_components.jvc_projector.config_flow.JvcProjector",
        return_value=projector,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert result["type"] is FlowResultType.FORM
        with patch(
            "custom_components.jvc_projector.async_setup_entry", return_value=True
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_HOST: projector.host, CONF_PORT: 20554}
            )
            await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_PASSWORD] is None
    projector.disconnect.assert_awaited_once()


async def test_setup_failure_cleans_connection(hass, projector):
    projector.get_state.side_effect = JvcProjectorConnectError("offline")
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_HOST: projector.host}, unique_id="aa:bb:cc:dd:ee:ff"
    )
    entry.add_to_hass(hass)
    with patch("custom_components.jvc_projector.JvcProjector", return_value=projector):
        assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert projector.disconnect.await_count >= 1


async def test_reauth_allows_clearing_password_and_preserves_data(hass, projector):
    entry = await setup_entry(hass, projector)
    hass.config_entries.async_update_entry(
        entry, data={**entry.data, CONF_PASSWORD: "old", "future_option": "keep"}
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    assert result["type"] is FlowResultType.FORM
    with (
        patch(
            "custom_components.jvc_projector.config_flow.JvcProjector",
            return_value=projector,
        ),
        patch("custom_components.jvc_projector.JvcProjector", return_value=projector),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] is None
    assert entry.data["future_option"] == "keep"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_reauth_rejects_different_projector(hass, projector):
    entry = await setup_entry(hass, projector)
    projector.mac = "112233445566"
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "reauth", "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch(
        "custom_components.jvc_projector.config_flow.JvcProjector",
        return_value=projector,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_device"
    assert CONF_PASSWORD not in entry.data
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_hdr_processing_enum_accepts_decoded_library_value(hass, projector):
    from custom_components.jvc_projector.sensor import JVC_SENSORS, JvcSensor

    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_HDR_PROCESSING: "frame"})
    description = next(d for d in JVC_SENSORS if d.key == const.KEY_HDR_PROCESSING)
    sensor = JvcSensor(coordinator, replace(description, translation_key=None))
    assert sensor.state == "frame"
    await coordinator.async_shutdown()


async def test_poll_and_remote_io_do_not_overlap(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    started = asyncio.Event()
    release = asyncio.Event()

    async def read_reference(code):
        started.set()
        await release.wait()
        return const.ON

    projector.ref.side_effect = read_reference
    refresh = asyncio.create_task(coordinator._async_update_data())
    await started.wait()
    remote = JvcProjectorRemote(coordinator)
    command = asyncio.create_task(remote.async_send_command(["up"]))
    await asyncio.sleep(0)
    projector.remote.assert_not_awaited()
    release.set()
    await asyncio.gather(refresh, command)
    projector.remote.assert_awaited_once()
    await coordinator.async_shutdown()


async def test_cancelled_inflight_command_disconnects(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    started = asyncio.Event()

    async def remote(code):
        started.set()
        await asyncio.Event().wait()

    projector.remote.side_effect = remote
    entity = JvcProjectorRemote(coordinator)
    task = asyncio.create_task(entity.async_send_command(["up"], hold_secs=2))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    projector.disconnect.assert_awaited_once()
    await coordinator.async_shutdown()


async def test_modern_controls_and_disabled_diagnostics(hass, projector):
    """New model controls register, while disabled diagnostics add no polls."""
    projector.model = "NZ900"
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    allm_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_{const.KEY_ALLM}"
    )
    black_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_{const.KEY_DEEP_BLACK}"
    )
    filmmaker_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_{const.KEY_FILMMAKER_AUTO}"
    )
    depth_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.unique_id}_{const.KEY_DEEP_COLOR}"
    )
    color_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{entry.unique_id}_{const.KEY_COLORIMETRY}"
    )
    assert allm_id and black_id and filmmaker_id and depth_id and color_id
    assert registry.async_get(allm_id).disabled_by is None
    assert registry.async_get(black_id).disabled_by is None
    assert registry.async_get(filmmaker_id).disabled_by is not None
    assert registry.async_get(depth_id).disabled_by is not None
    assert registry.async_get(color_id).disabled_by is not None
    await entry.runtime_data.async_refresh()
    requested = projector.get_state.call_args.kwargs["requested_keys"]
    assert {const.KEY_ALLM, const.KEY_DEEP_BLACK} <= requested
    assert not requested & {
        const.KEY_FILMMAKER_AUTO,
        const.KEY_DEEP_COLOR,
        const.KEY_COLORIMETRY,
    }
    await hass.services.async_call(
        "select", "select_option", {"entity_id": allm_id, "option": "on"}, blocking=True
    )
    projector.send_command.assert_awaited_with(const.KEY_ALLM, "on")
    registry.async_update_entity(depth_id, disabled_by=None)
    with patch("custom_components.jvc_projector.JvcProjector", return_value=projector):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    await entry.runtime_data.async_refresh()
    assert (
        const.KEY_DEEP_COLOR in projector.get_state.call_args.kwargs["requested_keys"]
    )
    assert (
        const.KEY_COLORIMETRY
        not in projector.get_state.call_args.kwargs["requested_keys"]
    )
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_legacy_model_has_no_unverified_modern_controls(hass, projector):
    projector.model = "NZ8"
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    assert registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_picture_mode"
    )
    for key in (const.KEY_ALLM, const.KEY_DEEP_BLACK, const.KEY_FILMMAKER_AUTO):
        assert (
            registry.async_get_entity_id("select", DOMAIN, f"{entry.unique_id}_{key}")
            is None
        )
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_modern_picture_modes_are_scoped_to_latest_spec(hass, projector):
    projector.model = "NZ900"
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_picture_mode"
    )
    options = hass.states.get(entity_id).attributes["options"]
    assert {"filmmaker", "vivid", "natural_ll", "hdr10_ll", "hlg_ll"} <= set(options)
    assert not {"animation", "thx", "pana_pq"} & set(options)
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "filmmaker"},
        blocking=True,
    )
    projector.send_command.assert_awaited_with("picture_mode", "filmmaker")
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_added_remote_shortcuts_use_spec_codes(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    remote = JvcProjectorRemote(coordinator)
    await remote.async_send_command(
        ["hide_on", "hide_off", "mode_10", "hdr10_plus", "filmmaker"], delay_secs=0
    )
    assert [call.args[0] for call in projector.remote.call_args_list] == [
        "73D0",
        "73D1",
        "73EB",
        "73F9",
        "73FB",
    ]
    await coordinator.async_shutdown()


@pytest.mark.parametrize(
    "key,value",
    [
        (const.KEY_HDR, "hdr10_plus"),
        (const.KEY_HDR_PROCESSING, "hdr10_plus"),
        (const.KEY_HDR_CONTENT_TYPE, "hdr10_plus"),
        (const.KEY_COLOR_SPACE, "ycbcr420"),
        (const.KEY_DEEP_COLOR, "12bit"),
        (const.KEY_COLORIMETRY, "dci_p3_d65"),
    ],
)
async def test_spec_enum_values_are_valid_sensor_states(hass, projector, key, value):
    from custom_components.jvc_projector.sensor import JVC_SENSORS, JvcSensor

    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({key: value})
    description = next(d for d in JVC_SENSORS if d.key == key)
    sensor = JvcSensor(coordinator, replace(description, translation_key=None))
    assert sensor.state == value
    await coordinator.async_shutdown()


async def test_modern_dimming_uses_model_specific_labels(hass, projector):
    projector.model = "NZ900"
    projector.get_state.return_value = {
        const.KEY_POWER: const.ON,
        const.KEY_LASER_DIMMING: "balanced",
    }
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_{const.KEY_LASER_DIMMING}"
    )
    state = hass.states.get(entity_id)
    assert state.state == "balanced"
    assert state.attributes["options"] == ["off", "low", "high", "balanced"]
    await hass.services.async_call(
        "select",
        "select_option",
        {"entity_id": entity_id, "option": "low"},
        blocking=True,
    )
    projector.send_command.assert_awaited_with("laser_dimming", "low")
    remote_id = registry.async_get_entity_id("remote", DOMAIN, entry.unique_id)
    await hass.services.async_call(
        "remote",
        "send_command",
        {"entity_id": remote_id, "command": "laser_dimming,balanced"},
        blocking=True,
    )
    projector.send_command.assert_awaited_with("laser_dimming", "balanced")
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "remote",
            "send_command",
            {"entity_id": remote_id, "command": "laser_dimming,auto1"},
            blocking=True,
        )
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_legacy_picture_modes_exclude_new_firmware_only_modes(hass, projector):
    projector.model = "NZ8"
    entry = await setup_entry(hass, projector)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_picture_mode"
    )
    assert not {"vivid", "natural_ll", "hdr10_ll", "hlg_ll"} & set(
        hass.states.get(entity_id).attributes["options"]
    )
    dimming_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.unique_id}_{const.KEY_LASER_DIMMING}"
    )
    assert hass.states.get(dimming_id).attributes["options"] == [
        "off",
        "auto1",
        "auto2",
        "auto3",
    ]
    assert await hass.config_entries.async_unload(entry.entry_id)
