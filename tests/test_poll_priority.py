"""Status polling yields at acknowledged references instead of blocking input."""

import asyncio
from unittest.mock import call, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.jvc_projector._vendor.jvcprojector import const
from custom_components.jvc_projector._vendor.jvcprojector.error import (
    JvcProjectorAuthError,
    JvcProjectorConnectError,
)
from custom_components.jvc_projector.coordinator import (
    JvcProjectorDataUpdateCoordinator,
)
from custom_components.jvc_projector.remote import JvcProjectorRemote


async def test_input_preempts_remaining_references_without_disconnect(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.STANDBY})
    reference_started = asyncio.Event()
    finish_reference = asyncio.Event()

    async def get_state(*, reference_reader, **kwargs):
        power = await reference_reader(const.CMD_POWER)
        await reference_reader(const.CMD_INPUT)
        await reference_reader(const.CMD_PICTURE_MODE)
        return {const.KEY_POWER: power}

    async def ref(code):
        reference_started.set()
        await finish_reference.wait()
        return const.ON

    projector.get_state.side_effect = get_state
    projector.ref.side_effect = ref
    poll = asyncio.create_task(coordinator._async_update_data())
    await reference_started.wait()
    command = asyncio.create_task(
        coordinator.async_execute_command(lambda: projector.remote(const.REMOTE_UP))
    )
    await asyncio.sleep(0)
    projector.remote.assert_not_awaited()
    finish_reference.set()
    assert await poll == {const.KEY_POWER: const.STANDBY}
    await command
    projector.ref.assert_awaited_once_with(const.CMD_POWER)
    projector.remote.assert_awaited_once_with(const.REMOTE_UP)
    projector.disconnect.assert_not_awaited()

    # A new poll captures the new input generation and completes normally.
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.ON}
    assert projector.ref.await_args_list == [
        call(const.CMD_POWER),
        call(const.CMD_POWER),
        call(const.CMD_INPUT),
        call(const.CMD_PICTURE_MODE),
    ]
    await coordinator.async_shutdown()


async def test_input_waiting_before_poll_read_prevents_first_reference(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    async with coordinator._lens_lock:
        poll = asyncio.create_task(coordinator._async_update_data())
        await asyncio.sleep(0)
        command = asyncio.create_task(
            coordinator.async_execute_command(
                lambda: projector.remote(const.REMOTE_DOWN)
            )
        )
        await asyncio.sleep(0)
    assert await poll == {const.KEY_POWER: const.ON}
    await command
    projector.ref.assert_not_awaited()
    projector.remote.assert_awaited_once()
    projector.disconnect.assert_not_awaited()
    await coordinator.async_shutdown()


async def test_final_generation_check_returns_current_snapshot(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.STANDBY})
    decoding = asyncio.Event()
    finish_decoding = asyncio.Event()

    async def get_state(*, reference_reader, **kwargs):
        await reference_reader(const.CMD_POWER)
        decoding.set()
        await finish_decoding.wait()
        return {const.KEY_POWER: const.STANDBY}

    projector.get_state.side_effect = get_state
    poll = asyncio.create_task(coordinator._async_update_data())
    await decoding.wait()
    await coordinator.async_execute_command(lambda: projector.remote(const.REMOTE_UP))
    # A newer update must not be overwritten by the old poll's delayed return.
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    finish_decoding.set()
    assert await poll == {const.KEY_POWER: const.ON}
    assert coordinator.data == {const.KEY_POWER: const.ON}
    projector.disconnect.assert_not_awaited()
    await coordinator.async_shutdown()


async def test_reference_boundary_yields_even_for_immediate_replies(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.STANDBY})
    command_tasks = []

    async def get_state(*, reference_reader, **kwargs):
        await reference_reader(const.CMD_POWER)
        command_tasks.append(
            asyncio.create_task(
                coordinator.async_execute_command(
                    lambda: projector.remote(const.REMOTE_OK)
                )
            )
        )
        await reference_reader(const.CMD_INPUT)
        return {const.KEY_POWER: const.ON}

    projector.get_state.side_effect = get_state
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.STANDBY}
    await asyncio.gather(*command_tasks)
    projector.ref.assert_awaited_once_with(const.CMD_POWER)
    projector.remote.assert_awaited_once_with(const.REMOTE_OK)
    await coordinator.async_shutdown()


async def test_poll_connects_again_after_foreground_failure(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    projector.connect.side_effect = [JvcProjectorConnectError("offline"), None]
    with pytest.raises(HomeAssistantError, match="offline"):
        await coordinator.async_execute_command(
            lambda: projector.remote(const.REMOTE_UP)
        )
    projector.remote.assert_not_awaited()
    projector.disconnect.assert_awaited_once()
    assert await coordinator._async_update_data() == {const.KEY_POWER: const.STANDBY}
    assert projector.connect.await_count == 2
    projector.ref.assert_awaited_once_with(const.CMD_POWER)
    await coordinator.async_shutdown()


async def test_failed_reference_discards_transport_and_reports_poll_failure(
    hass, projector
):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    projector.ref.side_effect = JvcProjectorConnectError("reference ACK lost")
    with pytest.raises(UpdateFailed, match="reference ACK lost"):
        await coordinator._async_update_data()
    projector.ref.assert_awaited_once()
    projector.disconnect.assert_awaited_once()
    await coordinator.async_shutdown()


async def test_failed_motor_stop_recovery_preserves_reauthentication(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator._lens_direction = "focus_near"
    projector.lens_move.side_effect = JvcProjectorAuthError("password changed")
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()
    projector.get_state.assert_not_awaited()
    # Permit final cleanup without repeating an intentional authentication failure.
    projector.lens_move.side_effect = None
    await coordinator.async_shutdown()


@pytest.mark.parametrize("action", ["turn_on", "turn_off", "setting"])
async def test_next_key_preempts_post_command_refresh(hass, projector, action):
    """A successful setting/power write must release the remote sequence lock."""
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    coordinator.async_set_updated_data({const.KEY_POWER: const.ON})
    remote = JvcProjectorRemote(coordinator)
    reading = asyncio.Event()
    finish_read = asyncio.Event()

    async def get_state(*, reference_reader, **kwargs):
        await reference_reader(const.CMD_POWER)
        await reference_reader(const.CMD_INPUT)
        return {const.KEY_POWER: const.ON}

    async def ref(code):
        reading.set()
        await finish_read.wait()
        return const.ON

    projector.get_state.side_effect = get_state
    projector.ref.side_effect = ref
    operation = {
        "turn_on": remote.async_turn_on,
        "turn_off": remote.async_turn_off,
        "setting": lambda: remote.async_send_command(["power,on"]),
    }[action]
    with (
        patch.object(
            coordinator,
            "async_request_refresh",
            side_effect=coordinator._async_update_data,
        ),
        patch("custom_components.jvc_projector.remote.MIN_COMMAND_DELAY", 0),
    ):
        first = asyncio.create_task(operation())
        await reading.wait()
        second = asyncio.create_task(remote.async_send_command(["up"]))
        await asyncio.sleep(0)
        finish_read.set()
        await asyncio.gather(first, second)
    projector.ref.assert_awaited_once_with(const.CMD_POWER)
    projector.remote.assert_awaited_once_with(const.REMOTE_UP)
    projector.disconnect.assert_not_awaited()
    await coordinator.async_shutdown()


@pytest.mark.parametrize("action", ["turn_on", "turn_off", "setting"])
async def test_failed_write_does_not_request_followup_refresh(hass, projector, action):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)
    remote = JvcProjectorRemote(coordinator)
    projector.send_command.side_effect = JvcProjectorConnectError("write ack lost")
    operation = {
        "turn_on": remote.async_turn_on,
        "turn_off": remote.async_turn_off,
        "setting": lambda: remote.async_send_command(["power,on"]),
    }[action]
    with (
        patch.object(coordinator, "async_request_refresh") as refresh,
        pytest.raises(HomeAssistantError, match="write ack lost"),
    ):
        await operation()
    refresh.assert_not_awaited()
    await coordinator.async_shutdown()


async def test_whole_poll_retains_timeout_across_healthy_references(hass, projector):
    coordinator = JvcProjectorDataUpdateCoordinator(hass, projector)

    async def get_state(*, reference_reader, **kwargs):
        for code in (
            const.CMD_POWER,
            const.CMD_INPUT,
            const.CMD_PICTURE_MODE,
            const.CMD_SOURCE,
        ):
            await reference_reader(code)
        return {const.KEY_POWER: const.ON}

    async def ref(code):
        await asyncio.sleep(0.02)
        return const.ON

    projector.get_state.side_effect = get_state
    projector.ref.side_effect = ref
    with (
        patch("custom_components.jvc_projector.coordinator.CONNECTION_TIMEOUT", 0.05),
        pytest.raises(UpdateFailed, match="Unable to update projector"),
    ):
        await coordinator._async_update_data()
    # Each reference fits the budget individually; their total exceeds it.
    assert 2 <= projector.ref.await_count < 4
    projector.disconnect.assert_awaited_once()
    await coordinator.async_shutdown()
