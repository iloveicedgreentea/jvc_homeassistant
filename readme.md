# JVC Projectors Home Assistant Integration
This is a Home Assistant JVC Custom Component implementing my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_python)

Someone else made an official integration after this one, so this will remain a custom component. Unfortunately, the official integration is missing a lot of features.

## Features

All the features in my [JVC library](https://github.com/iloveicedgreentea/jvc_projector_python) including:

- Power
- Picture Modes
- Laser power and dimming
- Pretty much every JVC command
- HA Attributes for current settings like power state, picture mode, laser mode, input, etc
- and so on


Note: JVC projectors currently only support a single network connection at a time. If you're running other control systems or attempt to run the JVC AutoCal software, keep in mind you can only have one control system connected at a time.

## Installation

This is a custom component.

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
```

You can use the remote entity attributes in sensors, automations, etc.

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
        laser_value (0-100)
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
