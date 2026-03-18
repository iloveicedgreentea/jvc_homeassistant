# JVC Projector Remote Home Assistant

> [!IMPORTANT]  
> All this code has been incorporated into the official core integration and this version no longer works with the latest release


This is a rewrite of the JVC Integration that is in core. It adds a ton of features that were in my previous custom integration. It was originally meant to be in core, but I don't have time to deal with their review process. So this is a custom component that you can install via HACS.

It is using my fork of the [core library](https://github.com/iloveicedgreentea/pyjvcprojector)

## Features

- Power
- Picture Modes
- Laser power and dimming
- Selects
- Device Info
- Tons of sensors and data

Because everything is async, it will run each button/command in the order it received. so commands won't disappear from the queue due to JVCs PJ server requiring the handshake. It uses a single persistent connection so any delay you see is because of HA processing.

## Installation

Install HACS, then install the component by adding this as a custom repo
https://hacs.xyz/docs/faq/custom_repositories

You can also just copy all the files into your custom_components folder but then you won't have automatic updates.

Uninstall the old JVC integration if you have it installed. This will not work with the old one.

### Home Assistant Setup

Once installed, you need to restart. Then simply add the JVC projector via the integrations page.
