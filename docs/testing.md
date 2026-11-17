# Development and testing

The runtime is self-contained in `custom_components/jvc_projector`, including the private library and its MIT license. The component tests import that bundled copy and exercise real Home Assistant config entries, services, entity platforms, and unload/reload against a simulated projector.

## Component checks

Use Python 3.14. From this checkout:

```sh
uv venv --python 3.14 .venv-test
uv pip install --python .venv-test/bin/python -r requirements-test.txt
.venv-test/bin/python -m ruff check custom_components/jvc_projector tests tools --extend-exclude _vendor
.venv-test/bin/python -m ruff format --check custom_components/jvc_projector tests tools --extend-exclude _vendor
.venv-test/bin/python -m pytest -q tests
```

These install test dependencies on the development machine. Home Assistant does not need to install the bundled library. CI runs the same checks; vendored source keeps the upstream library's formatting rules.

The pinned test harness uses HA 2026.10.2. For the minimum supported HA 2026.9.1, use a separate environment with `pytest-homeassistant-custom-component==0.13.364` and its dependency versions. Tests cover command ordering, poll preemption, model gating, disabled diagnostics, reauthentication, private imports, and lens tap/hold cleanup.

The 1.2.0rc1 library is published as a pre-release. Verify the downloaded distribution's PyPI SHA256 and compare its package files with `_vendor/jvcprojector` when testing the released artifact. HA 2026.11.2 also passed a runtime smoke check of imports, service dispatch, lens taps, and watchdog cleanup with simulated projector I/O. The full regression suite remains on the pinned HA versions: the latest published test harness imports a logger helper removed in HA 2026.11.2 and cannot collect tests there.

## Standalone library checks

The active source library is `pyjvcprojector`. Run its tests separately, following its README. Its hardware test is opt-in: set `RUN_INTEGRATION=true`, `JVC_IP`, and, if needed, `JVC_PASSWORD`. The test reads identity and state and disconnects afterward. Keep credentials out of committed files.

## Refresh the bundled library

Check out the corresponding library revision beside this repository, then run:

```sh
python tools/sync_library.py
python tools/sync_library.py --check
```

Pass `--library /path/to/pyjvcprojector` for another location. The sync copies source, typing marker, license, and provenance metadata. It records the Git revision, whether source differs from that revision, and checksums of the copied files. After committing a library change, sync again so the integration records the committed revision.

The component's CI verifies bundled-file hashes and import isolation without requiring a sibling checkout. The standalone library has its own regression checks.

## Build an installation ZIP

```sh
python tools/prepare_test_bundle.py --output dist/jvc-test
```

This verifies the library sync and creates `dist/jvc-test/` and `dist/jvc-test.zip`, with the complete component, README, dashboard examples, protocol notes, and a SHA256 inventory. It refuses to overwrite an existing output; choose another name for a new build.

Copy the ZIP's entire `custom_components/jvc_projector` directory into the HA config's `custom_components` directory, then restart HA. Existing JVC config entries are reused. Keep a backup of the previous component outside `custom_components`. To roll back, restore it and restart; removing the custom override returns to HA's built-in integration. See the repository README for migration from the old plural folder.

## Hardware checks

Test with one active network controller connected to the projector. Automated protocol tests cannot verify every model's behavior.

1. Start in standby; check identity and power state, then power on and verify signal and input state.
2. Check Menu, arrows, OK, Back, Info, Hide, and input selection. Verify repeat ordering and clear errors for failed commands.
3. Use the README's Bubble template to check lens focus, zoom, and shift. A tap should make one finite adjustment; holding for about 350 ms should start continuous movement; release should stop it.
4. Hold a lens control to the five-second safety interval and verify the stop request. Check direction switching and unloading during a pending hold. Keep the physical remote available: TCP disconnect is not a motor-stop command, and network failure can prevent stop delivery.
5. Check supported selects and enable an optional diagnostic sensor. Switch SDR/HDR/no signal/standby and verify signal-dependent values become unknown when no longer applicable.
6. Interrupt and restore the connection while the lens is stationary. Commands should recover without duplicate writes; check reauthentication when applicable.

## Polling latency

Background polling yields after each complete reference when foreground input arrives. An interrupted snapshot is discarded and the TCP connection stays open. The current reference must finish or time out; reconnections and deliberate command queues can still add latency. The 200 ms command recovery gap and 30-second overall poll budget remain in place.

The polling-priority regression checks that a key runs after the current reference rather than the remaining batch, without a disconnect or stale-state publication. A controlled simulation with 120 ms responses reduced a command's completion time during an 11-reference poll from about 3.66 seconds to 0.43 seconds. This is a simulation result; user testing separately confirmed improved control response on the installed projector.

Use the README's coordinator debug logger to separate control-lock wait from exchange time when investigating a delay. These logs do not measure browser-to-HA delivery.
