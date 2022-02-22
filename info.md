# JVC Projector Remote Improved Home Assistant

This is the Home Assistant JVC Component implementing my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved)

## Features
All the features in my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_improved) including:
* Power
* Picture Modes
* Laser power and dimming
* Low Latency meta-functions
* Optimal gaming and movie setting meta-functions
* and so on 

## Home Assistant Setup

```yaml
# configuration.yaml
remote:
  - platform: jvc_projectors
    name: {friendly name}
    password: {password}
    host: {IP addr}
    scan_interval: 30 # recommend 30-60. Power state will poll in this interval
```

## Useful Stuff
I used this to re-create the JVC remote in HA. Add the YAML to your dashboard to get a grid which resembles most of the remote. Other functions can be used via remote.send_command. See the library readme for details.
*Note: the remote.send_command service currently expects a list and the HA UI does not seem to allow you to specify a YAML list in the command param to the entity. If you use UI mode, you will break your config and get an index out of range error*

*Make sure to change your entity ID*

```yaml
type: grid
cards:
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
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - up
      target:
        entity_id: remote.nz7
    show_name: false
    show_icon: true
    icon: mdi:arrow-up
    hold_action:
      action: none
  - type: button
    tap_action:
      action: toggle
    show_icon: false
    show_name: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - menu
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
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - left
      target:
        entity_id: remote.nz7
    show_name: false
    icon: mdi:arrow-left
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - ok
      target:
        entity_id: remote.nz7
    name: OK
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - right
      target:
        entity_id: remote.nz7
    show_name: false
    icon: mdi:arrow-right
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - back
      target:
        entity_id: remote.nz7
    name: Back
    show_icon: false
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - menu
          - down
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
    name: Setup
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
        command:
          - power
          - 'off'
      target:
        entity_id: remote.nz7
    show_icon: false
    name: 'Off'
  - type: button
    tap_action:
      action: toggle
    show_icon: false
  - type: button
    tap_action:
      action: call-service
      service: remote.send_command
      service_data:
        command:
          - power
          - 'on'
      target:
        entity_id: remote.nz7
    name: 'On'
    show_icon: false
  - type: button
    tap_action:
      action: toggle
    show_icon: false
columns: 5
```
