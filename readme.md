# JVC Projector Remote Improved Home Assistant

This is the Home Assistant JVC Component implementing my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved)

## Features

All the features in my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved) including:

- Power
- Picture Modes
- Laser power and dimming
- Low Latency meta-functions
- Optimal gaming and movie setting meta-functions
- and so on

Because everything is async, it will run each button/command in the order it received. so commands won't disappear from the queue due to JVCs PJ server requiring the handshake. It uses a single persistent connection so any delay you see is because of HA processing.

## Installation

This is currently only a custom component. Unlikely to make it into HA core because their process is just too burdensome.

Install HACS, then install the component by adding this as a custom repo
https://hacs.xyz/docs/faq/custom_repositories

You can also just copy all the files into your custom_components folder but then you won't have automatic updates.

## Supported Commands

`$command,$mode`
example: "anamorphic,off"

```
Currently Supported Commands:
        anamorphic
        aperture
        enhance
        eshift
        graphic_mode
        input
        installation_mode
        laser_dim
        laser_power
        low_latency
        mask
        menu
        motion_enhance
        picture_mode
        power


Currently Supported Parameters:
AnamorphicModes
        off
        a
        b
        c
ApertureModes
        off
        auto1
        auto2
EnhanceModes
        zero
        one
        two
        three
        four
        five
        six
        seven
        eight
        nine
        ten
EshiftModes
        off
        on
GraphicModeModes
        standard
        hires1
        hires2
InputModes
        hdmi1
        hdmi2
InstallationModes
        mode1
        mode2
        mode3
        mode4
        mode5
        mode6
        mode7
        mode8
        mode9
        mode10
LaserDimModes
        off
        auto1
        auto2
LaserPowerModes
        low
        med
        high
LowLatencyModes
        off
        on
MaskModes
        on
        off
MenuModes
        menu
        up
        down
        back
        left
        right
        ok
MotionEnhanceModes
        off
        low
        high
PictureModes
        film
        cinema
        natural
        hdr
        THX
        frame_adapt_hdr
        user1
        user2
        user3
        user4
        user5
        user6
        hlg
        hdr_plus
        pana_pq
PowerModes
        off
        on
PowerStates
        standby
        on
        cooling
        reserved
        emergency
```

### Home Assistant Setup

```yaml
# configuration.yaml
remote:
  - platform: jvc_projectors
    name: { friendly name }
    password: { password }
    host: { IP addr }
    timeout: { seconds } (optional)
    scan_interval: 15 # recommend 15-30. Attributes will poll in this interval
```

## Useful Stuff

I used this to re-create the JVC remote in HA. Add the YAML to your dashboard to get a grid which resembles most of the remote. Other functions can be used via remote.send_command. See the library readme for details.

Add this sensor to your configuration.yml. Replace the nz7 with the name of your entity. Restart HA.

```yaml
sensor:
  platform: template
  sensors:
    jvc_low_latency:
      value_template: >
        {% if is_state('remote.nz7', 'on') %}
          {% if states.remote.nz7.attributes.low_latency == false %}
            Off
          {% elif states.remote.nz7.attributes.low_latency == true %}
            On
          {% endif %}
        {% else %}
            Off
        {% endif %}
```

Add this to lovelace

```yaml
type: grid
cards:
  - type: button
    name: Power
    show_icon: false
    entity: remote.nz7
    show_state: true
    show_name: true
    icon: mdi:power
  - type: button
    tap_action:
      action: call-service
      service: jvc_projectors.info
      service_data: {}
      target:
        entity_id: remote.nz7
    show_icon: false
    name: Info
    hold_action:
      action: none
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu,up
      target:
        entity_id: remote.nz7
    show_name: false
    show_icon: true
    icon: mdi:arrow-up
    hold_action:
      action: none
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu,menu
      target:
        entity_id: remote.nz7
    show_name: true
    show_icon: false
    name: Menu
    hold_action:
      action: none
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: none
    show_icon: false
    entity: sensor.jvc_low_latency
    show_name: true
    show_state: true
    name: Low Latency
    hold_action:
      action: none
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu,left
      target:
        entity_id: remote.nz7
    show_name: false
    icon: mdi:arrow-left
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu, ok
      target:
        entity_id: remote.nz7
    name: OK
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu, right
      target:
        entity_id: remote.nz7
    show_name: false
    icon: mdi:arrow-right
  - type: button
    tap_action:
      action: toggle
    show_icon: false
    show_name: false
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu,back
      target:
        entity_id: remote.nz7
    name: Back
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu,down
      target:
        entity_id: remote.nz7
    show_name: false
    icon: mdi:arrow-down
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: jvc_projectors.gaming_mode_hdr
      service_data: {}
      target:
        entity_id: remote.nz7
    show_icon: false
    show_name: true
    hold_action:
      action: none
    name: Game HDR
  - type: button
    tap_action:
      action: call-service
      service: jvc_projectors.gaming_mode_sdr
      service_data: {}
      target:
        entity_id: remote.nz7
    show_icon: false
    name: Game SDR
  - type: button
    tap_action:
      action: call-service
      service: jvc_projectors.hdr_picture_mode
      service_data: {}
      target:
        entity_id: remote.nz7
    show_icon: false
    name: Film HDR
  - type: button
    tap_action:
      action: call-service
      service: jvc_projectors.sdr_picture_mode
      service_data: {}
      target:
        entity_id: remote.nz7
    show_icon: false
    name: Film SDR
  - type: button
    tap_action:
      action: toggle
    show_icon: false
columns: 5
```
