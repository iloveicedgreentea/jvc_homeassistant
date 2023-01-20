# JVC Projector Remote Improved Home Assistant

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
    name: { friendly name }
    password: { password }
    host: { IP addr }
    timeout: { seconds } (optional)
    scan_interval: 15 # recommend 15-30. Attributes will poll in this interval
```

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
anamorphic:
        off
        a
        b
        c
        d
aperture:
        off
        auto1
        auto2
enhance:
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
eshift:
        off
        on
graphic_mode:
        standard
        hires1
        hires2
input:
        hdmi1
        hdmi2
installation_mode:
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
laser_dim:
        off
        auto1
        auto2
        auto3
laser_power:
        low
        med
        high
low_latency:
        off
        on
mask:
        on
        off
menu:
        menu
        up
        down
        back
        left
        right
        ok
motion_enhance:
        off
        low
        high
picture_mode:
        film
        cinema
        natural
        hdr
        THX
        frame_adapt_hdr
        frame_adapt_hdr2
        frame_adapt_hdr3
        filmmaker
        user1
        user2
        user3
        user4
        user5
        user6
        hlg
        hdr_plus
        pana_pq
power:
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
