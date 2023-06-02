# JVC Projectors Home Assistant Integration

This is the Home Assistant JVC Component implementing my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved)

## Features

All the features in my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved) including:

- Power
- Picture Modes
- Laser power and dimming
- Pretty much every JVC command
- HA Attributes for current settings like power state, picture mode, laser mode, input, etc
- and so on

It will run each button/command in the order it received. so commands won't disappear from the queue due to JVCs PJ server requiring the handshake. It uses a single persistent connection so any delay you see is because of their menu processing. In my experience it is noticably faster than IR control, ex. I can run about 10 commands per second.

Note: JVC projectors currently only support a single network connection at a time. If you're running other control systems or attempt to run the JVC AutoCal software, keep in mind you can only have one control system connected at a time.

Note: Only NX and NZ series are officially supported.

## Installation

This is currently only a custom component. Unlikely to make it into HA core because their process is just too burdensome and I strongly disagree with their deployment model for integrations.

Install HACS, then install the component by adding this as a custom repo
https://hacs.xyz/docs/faq/custom_repositories

You can also just copy all the files into your custom_components folder but then you won't get automatic updates.

### Home Assistant Setup

```yaml
# configuration.yaml
remote:
  - platform: jvc_projectors
    name: { entity name }
    password: { password } (optional for non-NZ)
    host: { IP addr }
    timeout: { seconds } (optional defaults to 3)
    scan_interval: 15 # recommend 15-30. Attributes will poll in this interval
```

If you set your scan interval too small you will get update errors because JVC projectors only accept a single command at a time so async is not possible. 

You can use the attributes in sensors, automations, etc.

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

## Usage

Use the `remote.send_command` service to send commands to the projector. 

`$command,$parameter`
example: "anamorphic,off"
example: "anamorphic,d"
example: "laser_dim,auto3"

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

Add this to lovelace

```yaml
square: false
columns: 3
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
  - show_name: false
    show_icon: true
    type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: menu, ok
      target:
        entity_id: remote.nz7
    name: OK
    icon: mdi:checkbox-blank-circle
    show_state: true
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
  - show_name: true
    show_icon: true
    type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: installation_mode,mode5
      target:
        entity_id: remote.nz7
    name: '17:9'
    icon: mdi:television
    show_state: false
  - show_name: true
    show_icon: true
    type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: installation_mode,mode4
      target:
        entity_id: remote.nz7
    name: 2.4:1
    icon: mdi:television
    show_state: false
  - show_name: true
    show_icon: true
    type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command: installation_mode,mode2
      target:
        entity_id: remote.nz7
    name: IMAX
    icon: mdi:television
    show_state: false
```
