# JVC Projectors Home Assistant Integration

This is the Home Assistant JVC Component implementing my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved)

## Features

All the features in my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved) including:

- Config Flow/UI setup
- Power
- Picture Modes
- Laser power and dimming
- Pretty much every JVC command
- Entity Attributes for current settings like power state, picture mode, laser mode, input, etc
- Async processing

Note: JVC projectors currently only support a single network connection at a time. If you're running other control systems or attempt to run the JVC AutoCal software, keep in mind you can only have one control system connected at a time.

Note: Only NX and NZ series are officially supported but this should work with any JVC projector that has an ethernet port.

## Installation

This is currently only a custom component. Unlikely to make it into HA core because their process is just too burdensome.

Install HACS, then install the component by adding this repository as a custom repo. More details here - https://hacs.xyz/docs/faq/custom_repositories

You can also just copy all the files into your custom_components folder but then you won't have automatic updates.

### Home Assistant Setup
This uses Config Flow. Install the custom component, restart, then add an integration as you normally do. Search JVC, and find the one that shows a box icon next to it. There is an official JVC Integration but it is limited and unrelated to this one.

*upon HA restart, it will automatically reconnect. No action is needed from you*

### Adding attributes as sensors

replace nz7 with the name of your remote entity
```yaml
sensor:
  platform: template
  sensors:
    jvc_installation_mode:
        value_template: >
            {% if is_state('remote.nz7', 'on') %}
              {{ states.remote.nz7.attributes.installation_mode }}
            {% else %}
                Off
            {% endif %}
```

### Attributes

These are the attributes supported for the entity
* power_state
* signal_status
* picture_mode
* installation_mode
* laser_power
* laser_mode
* lamp_power
* model
* content_type
* content_type_trans (the transition - sdr or hdr)
* hdr_data
* hdr_processing
* hdr_level
* theater_optimizer
* low_latency
* input_mode
* input_level
* color_mode
* aspect_ratio
* eshift
* mask_mode
* software_version
* lamp_time

## Usage

Use the `remote.send_command` service to send commands to the projector. 

`$command,$parameter`
example: "anamorphic,off"
example: "anamorphic,d"
example: "laser_dim,auto3"

It also supports using remote codes as ASCII [found here](https://support.jvc.com/consumer/support/documents/DILAremoteControlGuide.pdf) (Code A only)

example: "remote,2E"

```
Currently Supported Commands:
        anamorphic
        aperture
        aspect_ratio
        color_mode
        content_type
        content_type_trans
        enhance
        eshift_mode
        get_model
        get_software_version
        graphic_mode
        hdr_data
        hdr_level
        hdr_processing
        input_level
        input_mode
        installation_mode
        lamp_power
        lamp_time
        laser_mode
        laser_power
        low_latency
        mask
        menu
        motion_enhance
        picture_mode
        power
        remote
        signal_3d
        source_status
        theater_optimizer


Currently Supported Parameters:
AnamorphicModes
        off
        a
        b
        c
        d
ApertureModes
        off
        auto1
        auto2
AspectRatioModes
        zoom
        auto
        native
ColorSpaceModes
        auto
        YCbCr444
        YCbCr422
        RGB
ContentTypeTrans
        sdr
        hdr10_plus
        hdr10
        hlg
ContentTypes
        auto
        sdr
        hdr10_plus
        hdr10
        hlg
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
HdrData
        sdr
        hdr
        smpte
        hybridlog
        hdr10_plus
        none
HdrLevel
        auto
        min2
        min1
        zero
        plus1
        plus2
HdrProcessing
        hdr10_plus
        static
        frame_by_frame
        scene_by_scene
InputLevel
        standard
        enhanced
        superwhite
        auto
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
LampPowerModes
        normal
        high
LaserModes
        off
        auto1
        auto2
        auto3
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
        lens_control
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
        thx
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
        filmmaker
        frame_adapt_hdr2
        frame_adapt_hdr3
PowerModes
        off
        on
PowerStates
        standby
        on
        cooling
        reserved
        emergency
SourceStatuses
        logo
        no_signal
        signal
TheaterOptimizer
        off
        on
ThreeD
        auto
        sbs
        ou
        2d
```

## Useful Stuff

I used this to re-create the JVC remote in HA. Add the YAML to your dashboard to get a grid which resembles most of the remote. Other functions can be used via remote.send_command. See the library readme for details.

Add this sensor to your configuration.yml. Replace the nz7 with the name of your entity. Restart HA.

### Automating HDR modes per Harmony activity
```yaml
alias: JVC - HDR PM Automation
description: ""
trigger:
  - platform: state
    entity_id:
      - remote.nz7
    attribute: content_type
condition:
  - condition: not
    conditions:
      - condition: state
        entity_id: remote.nz7
        attribute: content_type
        state: sdr
action:
  - if:
      - condition: state
        entity_id: select.harmony_hub_2_activities
        state: Game
    then:
      - service: remote.send_command
        data:
          command: picture_mode,hdr10
mode: single

```

### Remote in UI
```yaml
sensor:
- platform: template
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

Here is something to get you started. You can add buttons and sensors as needed. 

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
columns: 5
```
