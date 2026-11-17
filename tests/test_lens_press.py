"""One-step taps upgrade to continuous motion only for a current held press."""

import asyncio
from unittest.mock import call, patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.jvc_projector._vendor.jvcprojector import const
from custom_components.jvc_projector._vendor.jvcprojector.error import (
    JvcProjectorConnectError,
)
from custom_components.jvc_projector.const import DOMAIN
from custom_components.jvc_projector.coordinator import (
    JvcProjectorDataUpdateCoordinator,
)


async def test_quick_tap_service_sends_only_one_step(hass, projector):
    """Real HA press/release services produce one finite step for a tap."""
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
        "press_lens",
        {"entity_id": remote_id, "direction": "focus_near"},
        blocking=True,
    )
    await hass.services.async_call(
        DOMAIN, "stop_lens", {"entity_id": remote_id}, blocking=True
    )
    await asyncio.sleep(0.4)
    projector.lens_step.assert_awaited_once_with("focus_near")
    projector.lens_move.assert_not_awaited()
    assert entry.runtime_data._lens_hold_task is None
    assert entry.runtime_data._lens_press_token is None
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_hold_steps_then_starts_after_threshold_and_stops_on_release(
    hass, projector
):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_press_lens("zoom_tele")
    await asyncio.sleep(0.05)
    projector.lens_step.assert_awaited_once_with("zoom_tele")
    projector.lens_move.assert_not_awaited()
    await coordinator._lens_hold_task
    projector.lens_move.assert_awaited_once_with("zoom_tele", start=True)
    await coordinator.async_stop_lens()
    assert projector.lens_move.await_args_list == [
        call("zoom_tele", start=True),
        call("zoom_tele", start=False),
    ]
    assert projector.mock_calls.index(call.lens_step("zoom_tele")) < (
        projector.mock_calls.index(call.lens_move("zoom_tele", start=True))
    )
    await coordinator.async_shutdown()


async def test_release_during_step_ack_prevents_late_start(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    sent = asyncio.Event()
    acknowledge = asyncio.Event()

    async def step(direction):
        sent.set()
        await acknowledge.wait()

    projector.lens_step.side_effect = step
    press = asyncio.create_task(coordinator.async_press_lens("shift_up"))
    await sent.wait()
    release = asyncio.create_task(coordinator.async_stop_lens())
    await asyncio.sleep(0.4)
    acknowledge.set()
    await asyncio.gather(press, release)
    projector.lens_step.assert_awaited_once_with("shift_up")
    projector.lens_move.assert_not_awaited()
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_press_token is None
    await coordinator.async_shutdown()


async def test_release_while_queued_behind_poll_preserves_one_step(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    polling = asyncio.Event()
    finish_poll = asyncio.Event()

    async def read_reference(code):
        polling.set()
        await finish_poll.wait()
        return const.ON

    projector.ref.side_effect = read_reference
    poll = asyncio.create_task(coordinator._async_update_data())
    await polling.wait()
    press = asyncio.create_task(coordinator.async_press_lens("focus_far"))
    await asyncio.sleep(0)
    release = asyncio.create_task(coordinator.async_stop_lens())
    await asyncio.sleep(0)
    finish_poll.set()
    await asyncio.gather(poll, press, release)
    projector.lens_step.assert_awaited_once_with("focus_far")
    projector.lens_move.assert_not_awaited()
    assert coordinator._lens_press_token is None
    await coordinator.async_shutdown()


async def test_release_while_stopping_previous_motor_preserves_one_step(
    hass, projector
):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("shift_up")
    stopping = asyncio.Event()
    acknowledge = asyncio.Event()

    async def lens_move(direction, *, start):
        if not start:
            stopping.set()
            await acknowledge.wait()

    projector.lens_move.side_effect = lens_move
    press = asyncio.create_task(coordinator.async_press_lens("focus_near"))
    await stopping.wait()
    release = asyncio.create_task(coordinator.async_stop_lens())
    await asyncio.sleep(0)
    acknowledge.set()
    await asyncio.gather(press, release)
    projector.lens_step.assert_awaited_once_with("focus_near")
    assert projector.lens_move.await_args_list == [
        call("shift_up", start=True),
        call("shift_up", start=False),
    ]
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_direction is None
    await coordinator.async_shutdown()


async def test_queued_taps_each_step_once_without_obsolete_promotion(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    async with coordinator._lens_lock:
        first = asyncio.create_task(coordinator.async_press_lens("focus_near"))
        await asyncio.sleep(0)
        second = asyncio.create_task(coordinator.async_press_lens("focus_far"))
        await asyncio.sleep(0)
        release = asyncio.create_task(coordinator.async_stop_lens())
        await asyncio.sleep(0)
    await asyncio.gather(first, second, release)
    assert projector.lens_step.await_args_list == [
        call("focus_near"),
        call("focus_far"),
    ]
    projector.lens_move.assert_not_awaited()
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_press_token is None
    await coordinator.async_shutdown()


async def test_shutdown_during_previous_stop_prevents_new_step(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_start_lens("shift_up")
    stopping = asyncio.Event()
    acknowledge = asyncio.Event()

    async def lens_move(direction, *, start):
        if not start:
            stopping.set()
            await acknowledge.wait()

    projector.lens_move.side_effect = lens_move
    press = asyncio.create_task(coordinator.async_press_lens("focus_near"))
    await stopping.wait()
    shutdown = asyncio.create_task(coordinator.async_shutdown())
    await asyncio.sleep(0)
    acknowledge.set()
    with pytest.raises(HomeAssistantError, match="unloading"):
        await press
    await shutdown
    projector.lens_step.assert_not_awaited()
    assert projector.lens_move.await_args_list == [
        call("shift_up", start=True),
        call("shift_up", start=False),
    ]
    assert projector.mock_calls[-1] == call.disconnect()
    assert coordinator._lens_hold_task is None


async def test_new_press_cancels_obsolete_direction_timer(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    with patch("custom_components.jvc_projector.coordinator.LENS_HOLD_DELAY", 0.01):
        await coordinator.async_press_lens("focus_near")
        old_timer = coordinator._lens_hold_task
        await coordinator.async_press_lens("focus_far")
        await coordinator._lens_hold_task
    assert old_timer.done()
    assert projector.lens_step.await_args_list == [
        call("focus_near"),
        call("focus_far"),
    ]
    projector.lens_move.assert_awaited_once_with("focus_far", start=True)
    await coordinator.async_stop_lens()
    await coordinator.async_shutdown()


async def test_failed_promotion_logs_and_explicitly_stops_without_replay(
    hass, projector, caplog
):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    projector.lens_move.side_effect = [JvcProjectorConnectError("start ack lost"), None]
    with patch("custom_components.jvc_projector.coordinator.LENS_HOLD_DELAY", 0.01):
        await coordinator.async_press_lens("zoom_wide")
        await coordinator._lens_hold_task
    projector.lens_step.assert_awaited_once_with("zoom_wide")
    assert projector.lens_move.await_args_list == [
        call("zoom_wide", start=True),
        call("zoom_wide", start=False),
    ]
    assert "Unable to start continuous lens movement after hold" in caplog.text
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_press_token is None
    assert coordinator._lens_direction is None
    await coordinator.async_shutdown()


@pytest.mark.parametrize("action", ["command", "shutdown", "start_lens"])
async def test_other_actions_cancel_pending_hold(hass, projector, action):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    await coordinator.async_press_lens("shift_left")
    timer = coordinator._lens_hold_task
    if action == "command":
        await coordinator.async_execute_command(
            lambda: projector.remote(const.REMOTE_UP)
        )
    elif action == "shutdown":
        await coordinator.async_shutdown()
    else:
        await coordinator.async_start_lens("zoom_wide")
    await asyncio.sleep(0.4)
    assert timer.done()
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_press_token is None
    if action == "start_lens":
        projector.lens_move.assert_awaited_once_with("zoom_wide", start=True)
        await coordinator.async_stop_lens()
    else:
        projector.lens_move.assert_not_awaited()
    await coordinator.async_shutdown()


async def test_default_watchdog_requests_five_seconds_from_continuous_start(
    hass, projector
):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    loop = asyncio.get_running_loop()
    with patch("custom_components.jvc_projector.coordinator.LENS_HOLD_DELAY", 0.01):
        await coordinator.async_press_lens("shift_right")
        with patch.object(coordinator, "_ensure_lens_watchdog") as watchdog:
            await coordinator._lens_hold_task
    deadline = watchdog.call_args.args[0]
    assert 4.8 < deadline - loop.time() <= 5
    await coordinator.async_stop_lens()
    await coordinator.async_shutdown()


async def test_short_watchdog_finishes_gesture_without_restarting(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    with patch("custom_components.jvc_projector.coordinator.LENS_HOLD_DELAY", 0.01):
        await coordinator.async_press_lens("focus_near", duration=0.01)
        await coordinator._lens_hold_task
        await coordinator._lens_watchdog
    await asyncio.sleep(0.05)
    assert projector.lens_move.await_args_list == [
        call("focus_near", start=True),
        call("focus_near", start=False),
    ]
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_press_token is None
    await coordinator.async_stop_lens()
    assert projector.lens_move.await_count == 2
    await coordinator.async_shutdown()


@pytest.mark.parametrize("failure", ["error", "cancel", "timeout"])
async def test_failed_or_cancelled_step_never_promotes(hass, projector, failure):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    sent = asyncio.Event()

    async def step(direction):
        sent.set()
        if failure == "error":
            raise JvcProjectorConnectError("step ack lost")
        await asyncio.Event().wait()

    projector.lens_step.side_effect = step
    with patch(
        "custom_components.jvc_projector.coordinator.LENS_COMMAND_TIMEOUT", 0.02
    ):
        task = asyncio.create_task(coordinator.async_press_lens("focus_far"))
        await sent.wait()
        if failure == "cancel":
            task.cancel()
        with pytest.raises(
            asyncio.CancelledError if failure == "cancel" else HomeAssistantError
        ):
            await task
    await asyncio.sleep(0.4)
    projector.lens_step.assert_awaited_once_with("focus_far")
    projector.lens_move.assert_not_awaited()
    assert coordinator._lens_hold_task is None
    assert coordinator._lens_press_token is None
    await coordinator.async_shutdown()


async def test_cancelled_queued_press_clears_token(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    async with coordinator._lens_lock:
        press = asyncio.create_task(coordinator.async_press_lens("focus_near"))
        await asyncio.sleep(0)
        press.cancel()
        with pytest.raises(asyncio.CancelledError):
            await press
    projector.lens_step.assert_not_awaited()
    assert coordinator._lens_press_token is None
    await coordinator.async_shutdown()


async def test_pending_gesture_pauses_poll_until_released(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    await coordinator.async_press_lens("shift_down")
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.ON}
    projector.get_state.assert_not_awaited()
    await coordinator.async_stop_lens()
    await coordinator._async_update_data()
    projector.get_state.assert_awaited_once()
    await coordinator.async_shutdown()


@pytest.mark.parametrize("direction,model", [("bad", "NZ7"), ("focus_near", "NX7")])
async def test_invalid_press_never_steps(hass, projector, direction, model):
    projector.model = model
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    with pytest.raises(ServiceValidationError):
        await coordinator.async_press_lens(direction)
    projector.lens_step.assert_not_awaited()
    projector.lens_move.assert_not_awaited()
    assert coordinator._lens_press_token is None
    await coordinator.async_shutdown()
