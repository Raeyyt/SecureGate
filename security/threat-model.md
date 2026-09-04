# SecureGate Threat Model

## System Overview

SecureGate is a physical access-control and intrusion-detection system built on an
Arduino UNO. It authenticates users via RFID card + PIN (two-factor), detects
motion in the monitored area, logs all security-relevant events with timestamps,
and forwards those events to a PC-based collector and live dashboard.

## Assets Being Protected

- **Physical access** to whatever space/enclosure the relay-controlled lock guards
- **Integrity of the authentication process** (card + PIN check)
- **Integrity and availability of the security event log** (used for after-the-fact
  investigation)
- **Availability of the detection system itself** (an attacker disabling the sensor
  is itself a security failure)

## Actors / Threat Sources

| Actor | Motivation | Capability |
|---|---|---|
| Opportunistic intruder | Gain unauthorized physical entry | Low - no special tools, may find/steal a card |
| Persistent attacker | Defeat the access control deliberately | Medium - may attempt brute force, tampering, or sensor evasion |
| Insider (e.g. someone with legitimate PIN knowledge) | Access outside their authorization, or share credentials | Varies |

## In-Scope Threats

1. **Unauthorized RFID card use** - a card that hasn't been enrolled attempting authentication.
   - *Mitigation:* UID allowlist check (`checkUID()`); every failed match is logged as `RFID_AUTH_FAILURE`.

2. **PIN brute-forcing** - repeated guessing of the numeric PIN.
   - *Mitigation:* lockout after 3 consecutive failed attempts, 30-second cooldown,
     logged as `BRUTE_FORCE_DETECTED`. This trades a small amount of legitimate-user
     friction for meaningfully raising the cost of guessing.

3. **Unauthorized presence / tailgating** - someone entering the monitored space
   without going through the card+PIN flow at all (e.g. propping a door, following
   an authorized user in).
   - *Mitigation:* PIR motion sensor runs independently of the authentication flow
     and logs `INTRUSION_DETECTED` any time motion is sensed, regardless of whether
     an authentication attempt is in progress.

4. **Tampering with the log pipeline** - an attacker with access to the PC deleting
   or editing `securegate_log.jsonl` to cover their tracks.
   - *Partial mitigation:* out of scope for the current version (see below), but
     acknowledged as a real gap - see Limitations.

## Out-of-Scope / Explicitly Not Defended Against

Being explicit about what this system does *not* protect against is as important as
what it does:

- **Card cloning/spoofing at the RF level.** The MFRC522 + basic MIFARE UID check
  used here does not implement cryptographic card authentication. A sufficiently
  capable attacker with proximity to a legitimate card could clone its UID. This is
  a known limitation of low-cost RFID access systems generally, not unique to this
  build.
- **Physical bypass of the enclosure itself** (e.g. forcing the door, cutting power
  to the Arduino). SecureGate is a logical access-control layer, not a substitute
  for physical hardening.
- **Network-based attacks.** The current (Stage 1-11) build has no network exposure -
  the Arduino talks to the PC only over a wired USB/serial connection, and the
  dashboard is served locally. This significantly reduces attack surface but is
  also why network security isn't discussed further here. (The planned ESP32
  upgrade, if built, would need its own threat model addressing Wi-Fi/MQTT
  exposure, which is a materially different risk profile.)
- **Log tampering resistance.** As noted above, log integrity (e.g. write-once
  storage, cryptographic signing of log entries) is not implemented in this
  version. A real production system would need this to be trustworthy as
  forensic evidence.
- **Denial of service against the sensor hardware.** Physically obstructing or
  disabling the PIR sensor (e.g. covering it) is not itself detected.

## Assumptions

- The Arduino, RFID reader, keypad, and PIR sensor are physically secured such
  that an attacker cannot easily rewire or replace them without detection.
- The PC running the collector/dashboard is a trusted, single-user machine.
- The authorized card and PIN are not shared or written down insecurely.

## Summary

SecureGate's primary value is as a **defense-in-depth logical layer**: two-factor
authentication, brute-force resistance, and independent motion-based intrusion
detection, all producing a structured, timestamped audit trail. It is explicitly
not a hardened, tamper-proof, or network-resilient system in its current form -
those gaps are documented here rather than glossed over, since a threat model that
only lists what a system defends against isn't a complete one.
