# JVC protocol references

Downloaded from JVC's current [installer/calibrator documentation](https://www.jvc.com/usa/projectors/installers-calibrators/) on 19 October 2026. The latest command revision linked there for the NZ800/NZ900 family is Ver. 2.0. These are family-specific documents, not proof that every older projector accepts the new settings.

- [External Command Communication Specification Ver. 2.0, 8 October 2025](https://www.jvc.com/content/dam/jvc/usa/projectors/installers-calibrators/External-command_for-LEO4(Ver2.0).pdf), 52 pages, document PJ14010001B. Covers NZ800/NZ900 and RS3200/RS4200 regional equivalents.
  Local file: `External-command-for-LEO4-Ver2.0.pdf`.
  SHA256: `cc2f96a5131290da0c512647a89c2309665158adabed38e6a94fb7f70efbd5f6`.
- [LAN connection specification Ver. 1.0, 9 December 2024](https://www.jvc.com/content/dam/jvc/usa/projectors/installers-calibrators/LANconnection_spec_2024_EN.pdf), 6 pages. Also covers NZ500/NZ700 and RS1200/RS2200.
  Local file: `LANconnection-spec-2024-EN.pdf`.
  SHA256: `97561ed19243f1513f8b516e32c0065e6808c0a13227b700945159670b3d77c6`.
- [2025 Remote Control Codes Table Ver. 2.1](https://www.jvc.com/content/dam/jvc/usa/projectors/installers-calibrators/LEO4-Remote-Control-Codes-Table-(ver-2-1).pdf), 1 page.
  Local file: `Remote-Control-Codes-LEO4-Ver2.1.pdf`.
  SHA256: `ceddc065b4a14553ea30f0409848e3d0e3d6184a3eae9b35fce686e3153cd1d2`.

The downloaded PDFs stay local and are ignored by Git. Follow the source links to retrieve them on a new checkout. The repository and local test ZIP include the provenance and audit notes without redistributing the PDFs.

## Audit findings and decisions

- The LAN specification p5 requires hashing the actual password plus `JVCKWPJ`. Padding a legacy password before hashing breaks modern authentication for shorter passwords. Keep padded legacy authentication separate from the SHA256 input.
- A busy `PJ_NG` handshake requires closing the connection before trying again. Read full fixed-size TCP messages even if fragmented. Close timed-out streams before the next command to avoid consuming a late reply out of sequence.
- Command specification p34, tables 4-35/36: HDR processing maps 0 to HDR10+, 1 to static, 2 to frame, 3 to scene. HDR content type 2 means HDR10+. HDR10+ processing is a reference-only value, so it cannot be written as a setting.
- P25: model suffixes `B8A1` and `B8A2` identify NZ900 and NZ800 families. Treating them as unknown prevents model-specific polling and controls from working.
- P29, p34–37, and p43–44 add or extend picture modes, HDR, graphics, colorimetry, resolution, ALLM, Deep Black, and Filmmaker configuration. Model-dependent fields must remain gated, and diagnostic-only entities should start disabled. Disabled optional entities should not generate their own polling traffic.
- P16–17 defines generic remote pass-through as four hexadecimal characters. There is no generic key-down/key-up frame. Repeated acknowledged keys are a simulation, including HA's `hold_secs`; physical IR long-press behavior on Advanced Menu/Info needs hardware verification.
- P48 gives a modern hyphenated firmware format. Retain compatibility with older firmware responses as well.

This is a focused audit of the supported protocol, controls, and telemetry. Bulk gamma uploads, panel alignment, installer calibration, and network reconfiguration remain outside the custom integration's UI. Their specialized multi-stage commands need dedicated implementations and tests if requested later. A numeric laser write range is not inferred solely from its decoder or three preset endpoints.

## Continuous lens movement (22 October 2026)

The [JVC-authored NZ7/NZ8/NZ9/NP5 specification PJ11010001B, Ver. 1.0, 27 July 2021](https://device.report/m/678cbfd4482203e534e73bcf1c1cb14453dbe947c6a02f970329fb43bceb7869.pdf) is available from a third-party document mirror. Its cover identifies the supported families. Pages 27–28 list `INFN`/`INFF` (focus near/far), `INZT`/`INZW` (zoom tele/wide), and `INSL`/`INSR`/`INSU`/`INSD` (shift). Page 38, table 4-51, defines ASCII `1` as motor start and `0` as motor stop. Page 29 allows only one motor at a time. These commands are also present in the official NZ800/NZ900 specification above (pages 28–29 and 38).

These are continuous motor commands, separate from generic remote pass-through and the `IN1*` single-step commands. The component uses explicit start/stop services with a bounded stop watchdog, including stop on release and shutdown. TCP disconnect is not documented to stop movement, and a network outage can prevent delivery of a stop. Motor starts must never be automatically replayed after an uncertain response. The old `INLC` command is absent from both examined command tables and is not used for native movement.

The command sequence requires awaiting the matching acknowledgement. It does not specify a further 200 ms post-ACK delay; the library retains that recovery gap between commands as a compatibility safeguard, while returning the final acknowledgement promptly. The 50 ms byte timing rule is an intra-frame rule, not an inter-command interval.

## Single-step lens adjustment (23 October 2026)

The command tables distinguish native single-step focus (`IN1N`/`IN1F`), zoom (`IN1T`/`IN1W`), and shift (`IN1L`/`IN1R`/`IN1U`/`IN1D`) from continuous motor commands. The single-step operations have data type **None** and transmit the bare four-character code with no appended start/stop parameter. See the NZ7-family specification page 28 and the NZ800/NZ900 specification page 28. Their finite operation can be sent immediately for a tap. The dashboard's press service sends one step, waits until the 350 ms hold threshold, and starts continuous movement only if the same press is still active. Release cancels promotion or explicitly stops continuous motion. The continuous-motion stop watchdog now defaults to 5 seconds.
