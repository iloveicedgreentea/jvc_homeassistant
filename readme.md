# JVC Projector Remote for Home Assistant

Control a network-connected JVC D-ILA projector with a remote, selects, and diagnostic sensors. The [projector library 1.2.0rc1 pre-release](https://github.com/iloveicedgreentea/pyjvcprojector/releases/tag/v1.2.0rc1) is bundled for testing; no extra Python package installation is required.

## Features

- Power, menu navigation, inputs, lens controls, and picture-mode remote keys.
- Selects for picture mode, input, installation mode, anamorphic mode, e-shift, and laser settings.
- NZ800/NZ900 ALLM and Deep Black controls, with optional Filmmaker auto mode.
- Disabled-by-default HDMI color-depth and colorimetry diagnostics, polled only when enabled.
- Power, signal, picture-mode, laser-hours, HDR, and resolution sensors, subject to your model and current signal. Extra diagnostic sensors start disabled.
- Standard `remote.send_command` repetition, delays, and bounded simulated holds.
- Native single-step lens taps, continuous movement after a 350 ms hold, and a five-second safety stop request.
- Status polling yields to controls between completed reads to reduce input delays.
- Ready-to-paste remote cards, with an optional repeat-while-pressed version.

## Installation and migration

Requires Home Assistant 2026.9.1 or later. Add this repository to HACS as an **Integration** through [Custom repositories](https://www.hacs.xyz/docs/faq/custom_repositories/), or copy the component folder manually.

The folder must be **`custom_components/jvc_projector`**, matching the domain. When upgrading, remove the old plural `jvc_projectors` folder; keep a backup outside `custom_components`.

This custom integration overrides HA's built-in integration of the same domain. Use one config entry per projector; do not add a second entry just to test the override. Back up the HA config before replacing an existing installation.

Copy the entire singular folder, including `_vendor`, into your HA config and restart Home Assistant. Existing JVC config entries are reused by the override; add **JVC Projector** through Settings → Devices & services only if you do not already have an entry. The library is bundled, so HA does not need to install it with pip. See [development and testing](docs/testing.md) for verification and rollback.

To refresh the bundled library during development, run `python tools/sync_library.py`, then `python tools/sync_library.py --check` to verify it matches the sibling `pyjvcprojector` source. The bundled copy includes the library’s MIT license and stays separate from a globally installed `jvcprojector` package.

## Remote dashboard

Choose standard HA buttons, repeating menu arrows with `custom:button-card`, or a Bubble popup with native lens tap/hold controls.

<details>
<summary>Standard Home Assistant cards</summary>

Add a **Manual** card to your dashboard and paste the YAML below. Replace **every** `remote.jvc_projector` with your remote entity ID.

This uses standard Home Assistant cards. Tapping an arrow sends one keypress; holding it starts a fixed 0.8-second burst.

```yaml
# Paste as a Manual card; replace every remote.jvc_projector with your entity ID.
# Standard HA cards only. Holding an arrow sends a fixed 0.8-second burst.
type: vertical-stack
cards:
  - type: grid
    columns: 2
    square: false
    cards:
      - type: button
        name: Power on
        icon: mdi:power
        tap_action:
          action: perform-action
          perform_action: remote.turn_on
          target:
            entity_id: remote.jvc_projector
        hold_action:
          action: none
      - type: button
        name: Standby
        icon: mdi:power-standby
        tap_action:
          action: perform-action
          perform_action: remote.turn_off
          target:
            entity_id: remote.jvc_projector
        hold_action:
          action: none
  - type: grid
    columns: 3
    square: true
    cards:
      - type: button
        name: Menu
        icon: mdi:menu
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: menu
        hold_action:
          action: none
      - type: button
        name: Up
        icon: mdi:chevron-up
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: up
        hold_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: up
            hold_secs: 0.8
      - type: button
        name: Info
        icon: mdi:information-outline
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: info
        hold_action:
          action: none
      - type: button
        name: Left
        icon: mdi:chevron-left
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: left
        hold_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: left
            hold_secs: 0.8
      - type: button
        name: OK
        icon: mdi:checkbox-marked-circle-outline
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: ok
        hold_action:
          action: none
      - type: button
        name: Right
        icon: mdi:chevron-right
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: right
        hold_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: right
            hold_secs: 0.8
      - type: button
        name: Back
        icon: mdi:arrow-u-left-top
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: back
        hold_action:
          action: none
      - type: button
        name: Down
        icon: mdi:chevron-down
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: down
        hold_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: down
            hold_secs: 0.8
      - type: button
        name: Hide
        icon: mdi:eye-off-outline
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: hide
        hold_action:
          action: none
  - type: grid
    columns: 2
    square: false
    cards:
      - type: button
        name: HDMI 1
        icon: mdi:video-input-hdmi
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: hdmi_1
        hold_action:
          action: none
      - type: button
        name: HDMI 2
        icon: mdi:video-input-hdmi
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.jvc_projector
          data:
            command: hdmi_2
        hold_action:
          action: none
```

</details>

<details>
<summary>Optional: repeat while you hold an arrow</summary>

Install [`custom:button-card`](https://github.com/custom-cards/button-card) through HACS, then add another **Manual** card and paste this YAML. Replace **every** `remote.jvc_projector` with your remote entity ID.

Arrows request a repeated press every 300 ms, up to 20 calls per hold. Release stops scheduling new calls; already queued calls may still finish. Increase the interval if your projector or network responds slowly. See the card's [repeat documentation](https://custom-cards.github.io/button-card/v7.0/config/actions/).

```yaml
# Optional: install custom:button-card through HACS first.
# Paste as a Manual card and replace remote.jvc_projector throughout.
# Hold an arrow to repeat while touching; release stops scheduling new calls.
# Pending calls can still finish. Increase repeat (milliseconds) on slow networks.
type: grid
columns: 3
square: true
cards:
  - type: custom:button-card
    name: Menu
    icon: mdi:menu
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: menu
  - type: custom:button-card
    name: Up
    icon: mdi:chevron-up
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: up
    hold_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: up
      repeat: 300
      repeat_limit: 20
  - type: custom:button-card
    name: Info
    icon: mdi:information-outline
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: info
  - type: custom:button-card
    name: Left
    icon: mdi:chevron-left
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: left
    hold_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: left
      repeat: 300
      repeat_limit: 20
  - type: custom:button-card
    name: OK
    icon: mdi:checkbox-marked-circle-outline
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: ok
  - type: custom:button-card
    name: Right
    icon: mdi:chevron-right
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: right
    hold_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: right
      repeat: 300
      repeat_limit: 20
  - type: custom:button-card
    name: Back
    icon: mdi:arrow-u-left-top
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: back
  - type: custom:button-card
    name: Down
    icon: mdi:chevron-down
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: down
    hold_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: down
      repeat: 300
      repeat_limit: 20
  - type: custom:button-card
    name: Hide
    icon: mdi:eye-off-outline
    tap_action:
      action: perform-action
      perform_action: remote.send_command
      target:
        entity_id: remote.jvc_projector
      data:
        command: hide
```

</details>

<details>
<summary>Bubble Card popup with held arrows and continuous lens controls</summary>

Install [Bubble Card](https://github.com/Clooos/Bubble-Card) and [custom:button-card](https://github.com/custom-cards/button-card) through HACS, then paste this into a **Manual** card. This version has no power controls.

The example uses `remote.nz7_2`; replace every occurrence with your remote entity ID. Keep `hash: '#jvc'` and open the popup from a dashboard button whose navigation action points to `#jvc`. Change the hash and `navigation_path: '#theater'` to match your dashboard if needed.

Hold a menu arrow to request a repeated press every 300 ms, up to 20 calls per hold. Releasing stops scheduling new calls; calls already queued may still finish. Increase `repeat` if your projector or network responds slowly.

The lens buttons below send one native lens step immediately on press. Keep holding for 350 ms to start continuous movement, then release to stop. They support NZ7/NZ8/NZ9/NP5 and NZ800/NZ900 families. Continuous movement automatically requests a stop after 5 seconds; release and press again for more movement. The stop still requires a working connection, so keep the physical remote available when testing. These buttons require this updated custom integration; they do not work with HA's built-in JVC integration.

```yaml
type: custom:bubble-card
card_type: pop-up
hash: '#jvc'
card_layout: large
close_action:
  action: navigate
  navigation_path: '#theater'
button_type: name
sub_button:
  main: []
  bottom: []
cards:
  - type: grid
    columns: 3
    square: true
    cards:
      - type: button
        name: Menu
        icon: mdi:menu
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: menu
        hold_action:
          action: none

      - type: custom:button-card
        name: Up
        icon: mdi:chevron-up
        show_name: false
        aspect_ratio: 1/1
        tap_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: up
        hold_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: up
          repeat: 300
          repeat_limit: 20

      - type: button
        name: Info
        icon: mdi:information-outline
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: info
        hold_action:
          action: none

      - type: custom:button-card
        name: Left
        icon: mdi:chevron-left
        show_name: false
        aspect_ratio: 1/1
        tap_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: left
        hold_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: left
          repeat: 300
          repeat_limit: 20

      - type: button
        name: OK
        icon: mdi:checkbox-marked-circle-outline
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: ok
        hold_action:
          action: none

      - type: custom:button-card
        name: Right
        icon: mdi:chevron-right
        show_name: false
        aspect_ratio: 1/1
        tap_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: right
        hold_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: right
          repeat: 300
          repeat_limit: 20

      - type: button
        name: Back
        icon: mdi:arrow-u-left-top
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: back
        hold_action:
          action: none

      - type: custom:button-card
        name: Down
        icon: mdi:chevron-down
        show_name: false
        aspect_ratio: 1/1
        tap_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: down
        hold_action:
          action: call-service
          service: remote.send_command
          target:
            entity_id: remote.nz7_2
          service_data:
            command: down
          repeat: 300
          repeat_limit: 20

      - type: button
        name: Hide
        icon: mdi:eye-off-outline
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: hide
        hold_action:
          action: none

  - type: grid
    columns: 3
    square: false
    cards:
      - type: button
        name: HDMI 1
        icon: mdi:video-input-hdmi
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: hdmi_1
        hold_action:
          action: none

      - type: button
        name: HDMI 2
        icon: mdi:video-input-hdmi
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: hdmi_2
        hold_action:
          action: none

      - type: button
        name: Lens Control
        icon: mdi:camera-control
        tap_action:
          action: perform-action
          perform_action: remote.send_command
          target:
            entity_id: remote.nz7_2
          data:
            command: lens_control
        hold_action:
          action: none

  - type: grid
    columns: 2
    square: false
    cards:
      - type: custom:button-card
        name: Shift left
        icon: mdi:arrow-left
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: shift_left
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Shift right
        icon: mdi:arrow-right
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: shift_right
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Shift up
        icon: mdi:arrow-up
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: shift_up
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Shift down
        icon: mdi:arrow-down
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: shift_down
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Focus near
        icon: mdi:focus-field
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: focus_near
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Focus far
        icon: mdi:focus-field
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: focus_far
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Zoom tele
        icon: mdi:magnify-plus-outline
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: zoom_tele
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
      - type: custom:button-card
        name: Zoom wide
        icon: mdi:magnify-minus-outline
        press_action:
          action: call-service
          service: jvc_projector.press_lens
          target:
            entity_id: remote.nz7_2
          service_data:
            direction: zoom_wide
            duration: 5
        release_action:
          action: call-service
          service: jvc_projector.stop_lens
          target:
            entity_id: remote.nz7_2
```

</details>

JVC's generic remote API sends acknowledged key codes. Menu-arrow holds simulate repeated presses and do not transmit an IR hold signal. Lens movement uses separate native motor start/stop commands in the Bubble example; it does not need repeated arrow presses. Other physical-remote long-press functions are not implied by this support.

## Native lens movement

The Bubble popup above includes focus, zoom, and shift controls for NZ7/NZ8/NZ9/NP5 and NZ800/NZ900 projectors. A press sends exactly one native single-step command. Holding for 350 ms starts continuous movement; release cancels the pending hold or stops the active motor. A quick tap does not send motor start/stop commands. An accepted tap still sends its single step if it was queued behind other I/O; release cancels only the continuous upgrade. The API is also available to custom dashboards:

```yaml
action: jvc_projector.press_lens
target:
  entity_id: remote.nz7_2
data:
  direction: shift_left
  duration: 5
```

```yaml
action: jvc_projector.stop_lens
target:
  entity_id: remote.nz7_2
```

Directions: `focus_near`, `focus_far`, `zoom_tele`, `zoom_wide`, `shift_left`, `shift_right`, `shift_up`, and `shift_down`. Duration defaults to 5 seconds and must be greater than zero and at most 5 seconds. It is the safety stop interval for continuous movement, measured from the continuous start attempt; it is not the threshold for recognizing a hold. Only one motor runs at a time; changing direction first stops the previous motor. Other controls cancel a pending hold and stop the motor before proceeding. Status polling pauses during a pending hold or continuous movement so it cannot delay a release. A status query already in flight must finish or time out before a control can use the connection. The remaining status queries yield to that input; partial snapshots are discarded.

Release, another control, or unloading the integration cancels a pending hold. Continuous movement also gets a stop request at the safety deadline or after an uncertain start response. Stop delivery requires network connectivity; the timer cannot guarantee a physical stop during a connection failure. Failed starts are never automatically replayed.

`jvc_projector.start_lens` remains available for immediate continuous movement with the same 5-second default. Dashboard buttons should use `press_lens` for tap/hold behavior.

## Actions

Simple names and the existing `remote,<name>` syntax both work:

```yaml
action: remote.send_command
target:
  entity_id: remote.jvc_projector
data:
  command: up
  num_repeats: 4
  delay_secs: 0.4
```

Send an ordered list, or set a named setting:

```yaml
action: remote.send_command
target:
  entity_id: remote.jvc_projector
data:
  command:
    - "remote,menu"
    - "remote,down"
    - "remote,ok"
```

```yaml
action: remote.send_command
target:
  entity_id: remote.jvc_projector
data:
  command: "picture_mode,natural"
```

To simulate a short held arrow, use `command: right` and `hold_secs: 0.8`. `hold_secs` applies only to remote keys. It is a fixed duration, independent of when you release a dashboard button. `num_repeats` repeats the entire command list. Communication time reduces the number of presses during a hold.

Limits: 1–100 repeats, 0–30 seconds per hold, 0–10 seconds between commands (minimum 0.1, default 0.2), and at most 1,000 estimated presses or 120 seconds per sequence. Failed commands surface as errors and are not blindly replayed.

Supported remote names: `menu`, `up`, `down`, `left`, `right`, `ok`, `back`, `mpc`, `hide`, `hide_on`, `hide_off`, `info`, `input`, `cmd`, `advanced_menu`, `picture_mode`, `color_profile`, `lens_control`, `setting_memory`, `gamma_settings`, `hdmi_1`, `hdmi_2`, `mode_1`, `mode_2`, `mode_3`, `mode_4`, `mode_5`, `mode_6`, `mode_7`, `mode_8`, `mode_9`, `mode_10`, `hdr10`, `hdr10_plus`, `hlg`, `filmmaker`, `lens_ap`, `gamma`, `color_temp`, `natural`, `cinema`, `anamo`, `3d_format`. Availability depends on your model.

## Protocol coverage

See [the specification audit](docs/specs/README.md) for JVC source URLs, document versions, local PDF checksums, and the fixes derived from them. Newer model-specific controls are exposed only for recognized NZ800/NZ900 models. JVC lists installation-memory recall as an operation without a matching status reference on these models: recall works, but its select state remains unknown. Numeric laser writes and installer calibration routines are intentionally not inferred from readback data.

## Control timing diagnostics

Status polling gives foreground controls priority between complete reference exchanges. A command no longer waits for the rest of a status batch, and the interrupted snapshot does not overwrite newer state. Commands and responses remain serialized; slow replies, reconnections, or a backlog of deliberate keypresses can still add latency. The 200 ms command recovery gap and the five-second lens stop watchdog remain in place.

To distinguish integration queueing from connection/projector response time, enable temporary debug logging:

```yaml
action: logger.set_level
data:
  custom_components.jvc_projector.coordinator: debug
```

Repeat a few presses and inspect the HA logs. `waited ... for control` measures the coordinator's control-lock wait; `queue ..., exchange ...` measures transport-lock wait and the operation, including any connection setup and command pacing. `Status poll interrupted by input` is a normal cooperative yield. These timings begin inside the integration and do not measure browser-to-HA delivery. Restore the logger to `info` when finished.
