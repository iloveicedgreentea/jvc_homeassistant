"""Native lens movement must always have a serialized, bounded stop path."""

import asyncio
from unittest.mock import call, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jvc_projector._vendor.jvcprojector import const
from custom_components.jvc_projector._vendor.jvcprojector.error import (
    JvcProjectorConnectError,
)
from custom_components.jvc_projector.const import DOMAIN
from custom_components.jvc_projector.coordinator import (
    JvcProjectorDataUpdateCoordinator,
)


async def test_lens_entity_services_start_and_release(hass, projector):
    """The actual HA entity services start once and stop on release."""
    projector.model = "NZ7"
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
    registry = er.async_get(hass)
    remote_id = registry.async_get_entity_id("remote", DOMAIN, entry.unique_id)
    await hass.services.async_call(
        DOMAIN,
        "start_lens",
        {"entity_id": remote_id, "direction": "focus_near", "duration": 0.15},
        blocking=True,
    )
    projector.lens_move.assert_awaited_once_with("focus_near", start=True)
    await hass.services.async_call(
        DOMAIN, "stop_lens", {"entity_id": remote_id}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, "stop_lens", {"entity_id": remote_id}, blocking=True
    )
    await asyncio.sleep(0.2)
    assert projector.lens_move.await_args_list == [
        call("focus_near", start=True),
        call("focus_near", start=False),
    ]
    assert entry.runtime_data._lens_watchdog is None
    await hass.services.async_call(
        DOMAIN,
        "start_lens",
        {"entity_id": remote_id, "direction": "shift_up"},
        blocking=True,
    )
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert projector.lens_move.await_args_list[-2:] == [
        call("shift_up", start=True),
        call("shift_up", start=False),
    ]
    assert projector.mock_calls[-1] == call.disconnect()


async def test_watchdog_stops_without_release(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("zoom_tele", duration=0.01)
    watchdog = coordinator._lens_watchdog
    await watchdog
    assert projector.lens_move.await_args_list == [
        call("zoom_tele", start=True),
        call("zoom_tele", start=False),
    ]
    assert coordinator._lens_direction is None
    assert coordinator._lens_watchdog is None
    await coordinator.async_shutdown()


async def test_switching_motors_and_other_commands_stop_first(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("focus_far")
    await coordinator.async_start_lens("shift_left")
    await coordinator.async_execute_command(lambda: projector.remote(const.REMOTE_UP))
    assert projector.lens_move.await_args_list == [
        call("focus_far", start=True),
        call("focus_far", start=False),
        call("shift_left", start=True),
        call("shift_left", start=False),
    ]
    assert projector.mock_calls.index(call.lens_move("shift_left", start=False)) < (
        projector.mock_calls.index(call.remote(const.REMOTE_UP))
    )
    await coordinator.async_shutdown()


async def test_release_waits_for_start_inflight(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    started = asyncio.Event()
    acknowledge = asyncio.Event()

    async def lens_move(direction, *, start):
        if start:
            started.set()
            await acknowledge.wait()

    projector.lens_move.side_effect = lens_move
    start_task = asyncio.create_task(coordinator.async_start_lens("shift_up"))
    await started.wait()
    stop_task = asyncio.create_task(coordinator.async_stop_lens())
    await asyncio.sleep(0)
    assert projector.lens_move.await_count == 1
    acknowledge.set()
    await asyncio.gather(start_task, stop_task)
    assert projector.lens_move.await_args_list == [
        call("shift_up", start=True),
        call("shift_up", start=False),
    ]
    await coordinator.async_shutdown()


async def test_uncertain_start_attempts_stop_without_replaying_start(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    projector.lens_move.side_effect = [JvcProjectorConnectError("ack lost"), None]
    with pytest.raises(HomeAssistantError, match="ack lost"):
        await coordinator.async_start_lens("zoom_wide")
    assert projector.lens_move.await_args_list == [
        call("zoom_wide", start=True),
        call("zoom_wide", start=False),
    ]
    projector.disconnect.assert_awaited_once()
    assert coordinator._lens_direction is None
    await coordinator.async_shutdown()


async def test_start_timeout_attempts_fresh_stop(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)

    async def lens_move(direction, *, start):
        if start:
            await asyncio.Event().wait()

    projector.lens_move.side_effect = lens_move
    with (
        patch("custom_components.jvc_projector.coordinator.LENS_COMMAND_TIMEOUT", 0.01),
        pytest.raises(HomeAssistantError, match="timed out"),
    ):
        await coordinator.async_start_lens("shift_down", duration=0.05)
    assert projector.lens_move.await_args_list == [
        call("shift_down", start=True),
        call("shift_down", start=False),
    ]
    projector.disconnect.assert_awaited_once()
    assert coordinator._lens_direction is None
    await coordinator.async_shutdown()


async def test_cancelled_start_explicitly_stops_motor(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    started = asyncio.Event()

    async def lens_move(direction, *, start):
        if start:
            started.set()
            await asyncio.Event().wait()

    projector.lens_move.side_effect = lens_move
    task = asyncio.create_task(coordinator.async_start_lens("focus_far"))
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert projector.lens_move.await_args_list == [
        call("focus_far", start=True),
        call("focus_far", start=False),
    ]
    projector.disconnect.assert_awaited_once()
    assert coordinator._lens_direction is None
    assert coordinator._lens_watchdog is None
    await coordinator.async_shutdown()


async def test_watchdog_deadline_includes_start_ack_wait(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)

    async def lens_move(direction, *, start):
        if start:
            await asyncio.sleep(0.04)

    projector.lens_move.side_effect = lens_move
    await coordinator.async_start_lens("focus_near", duration=0.01)
    # The requested duration elapsed while waiting for start; stop immediately.
    with patch(
        "custom_components.jvc_projector.coordinator.asyncio.sleep", wraps=asyncio.sleep
    ) as sleep:
        await coordinator._lens_watchdog
    assert sleep.await_args_list[0].args == (0,)
    assert coordinator._lens_direction is None
    await coordinator.async_shutdown()


async def test_poll_skips_during_motion_and_resumes_after_stop(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    await coordinator.async_start_lens("shift_right")
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.ON}
    projector.get_state.assert_not_awaited()
    await coordinator.async_stop_lens()
    await coordinator._async_update_data()
    projector.get_state.assert_awaited_once()
    await coordinator.async_shutdown()


async def test_exhausted_watchdog_retries_stop_during_later_poll(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    await coordinator.async_start_lens("focus_near", duration=0.01)
    projector.lens_move.side_effect = [
        JvcProjectorConnectError("offline"),
        JvcProjectorConnectError("offline"),
        JvcProjectorConnectError("offline"),
        JvcProjectorConnectError("offline"),
        None,
    ]
    await coordinator._lens_watchdog
    assert coordinator._lens_direction == "focus_near"
    assert coordinator._lens_watchdog is None
    with pytest.raises(UpdateFailed, match="offline"):
        await coordinator._async_update_data()
    projector.get_state.assert_not_awaited()
    await coordinator._async_update_data()
    assert coordinator._lens_direction is None
    projector.get_state.assert_awaited_once()
    await coordinator.async_shutdown()


async def test_shutdown_stops_before_disconnecting_and_retries(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("focus_far")
    projector.lens_move.side_effect = [JvcProjectorConnectError("stop ack lost"), None]
    await coordinator.async_shutdown()
    assert projector.lens_move.await_args_list == [
        call("focus_far", start=True),
        call("focus_far", start=False),
        call("focus_far", start=False),
    ]
    assert projector.mock_calls[-1] == call.disconnect()
    assert coordinator._lens_watchdog is None
    assert coordinator._lens_direction is None


async def test_failed_stop_retains_direction_for_release_retry(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("shift_left")
    projector.lens_move.side_effect = [JvcProjectorConnectError("stop ack lost"), None]
    with pytest.raises(HomeAssistantError, match="stop ack lost"):
        await coordinator.async_stop_lens()
    assert coordinator._lens_direction == "shift_left"
    assert coordinator._lens_watchdog is not None
    await coordinator.async_stop_lens()
    assert coordinator._lens_direction is None
    assert coordinator._lens_watchdog is None
    await coordinator.async_shutdown()


async def test_shutdown_stop_failures_are_bounded_and_reported(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("zoom_tele")
    projector.lens_move.side_effect = JvcProjectorConnectError("offline")
    with pytest.raises(HomeAssistantError, match="offline"):
        await coordinator.async_shutdown()
    assert projector.lens_move.await_count == 4
    assert coordinator._lens_direction == "zoom_tele"
    assert coordinator._lens_watchdog is None
    assert coordinator._stopped
    assert projector.mock_calls[-1] == call.disconnect()


@pytest.mark.parametrize("model", ["(unknown)", "NX7", "NZ500", "NZ700"])
async def test_unverified_model_never_sends_motor_commands(hass, projector, model):
    projector.model = model
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    with pytest.raises(ServiceValidationError, match="not verified"):
        await coordinator.async_start_lens("focus_near")
    projector.lens_move.assert_not_awaited()
    projector.connect.assert_not_awaited()
    await coordinator.async_shutdown()


@pytest.mark.parametrize(
    "duration", [True, 0, -1, 5.1, float("inf"), float("nan"), "3"]
)
async def test_invalid_duration_never_starts(hass, projector, duration):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    with pytest.raises(ServiceValidationError, match="duration"):
        await coordinator.async_start_lens("focus_near", duration)
    projector.lens_move.assert_not_awaited()
    await coordinator.async_shutdown()
