# SecureGate Attack Scenarios

This document walks through concrete ways an attacker might attempt to defeat
SecureGate, based on the threats identified in `threat-model.md`. Each scenario
describes the attack, how SecureGate responds today, and any residual risk.

---

## Scenario 1: Repeated PIN guessing at the keypad

**Attack:** An attacker who has obtained or cloned an authorized card (or is
standing at the keypad after someone else scanned a card) tries multiple PINs
in a row, hoping to guess the correct one.

**System response:**
1. First wrong PIN -> `PIN_AUTH_FAILURE` logged, `ACCESS_DENIED` logged
   (attempt 1/3).
2. Second wrong PIN -> same, attempt 2/3.
3. Third wrong PIN -> `BRUTE_FORCE_DETECTED` logged, system enters a 30-second
   lockout. Buzzer sounds once per second for the duration. All card scans and
   keypad input are ignored during lockout.

**Residual risk:** 30 seconds is a deliberately short lockout for a portfolio/demo
build. In a production deployment this would likely need to be longer, and
possibly escalate (e.g. doubling lockout duration on repeated lockouts within a
short window) to meaningfully slow down a patient attacker.

---

## Scenario 2: Unrecognized card presented repeatedly

**Attack:** An attacker without a valid card tries several different cards or
fobs against the reader, hoping one happens to match (or is simply probing the
system's behavior).

**System response:** Each unrecognized UID triggers `RFID_AUTH_FAILURE` and
counts toward the same 3-attempt lockout threshold as wrong PINs - the failure
counter does not distinguish between "wrong card" and "wrong PIN," so mixing
attack types doesn't help the attacker reset their attempt budget.

**Residual risk:** The UID allowlist is a single hardcoded value in the current
build (`authorizedUID[]`). This works for a single-user demo but doesn't scale -
a real deployment needs multiple enrolled UIDs and a way to add/revoke them
without reflashing the Arduino.

---

## Scenario 3: Someone enters the monitored space without authenticating

**Attack:** Rather than attacking the authentication flow at all, an attacker
props a door open, follows an authorized person through (tailgating), or
otherwise bypasses the card/PIN check entirely.

**System response:** The PIR motion sensor runs independently of the
authentication logic and logs `INTRUSION_DETECTED` the moment motion is sensed -
including in the middle of a legitimate person's PIN entry, and including when
no authentication attempt is happening at all. This is deliberate: physical
presence is monitored regardless of what the keypad/RFID flow is doing.

**Residual risk:** A single PIR sensor gives binary motion detection, not
identity or direction. It can't distinguish "an authorized person walked past"
from "an intruder entered" - it only tells you *that* something moved. In
practice this means `INTRUSION_DETECTED` events need to be cross-referenced
against `ACCESS_GRANTED` events (by timestamp) during log review to be useful,
rather than treated as a standalone alarm.

---

## Scenario 4: Attacker deletes or edits the log after an incident

**Attack:** Someone with access to the PC (or physical access to swap the SD
card/storage in a more advanced build) edits or deletes `securegate_log.jsonl`
after an unauthorized access event, to cover their tracks.

**System response:** None currently. The log file is a plain, unsigned,
locally-writable JSON Lines file with no integrity protection.

**Residual risk:** This is the most significant open gap in the current build,
and it's called out explicitly rather than glossed over. A real system would
need at least one of: append-only/write-protected storage, periodic remote
log shipping (so a local copy being tampered with isn't the only copy), or
cryptographic signing of each log entry so tampering is detectable even if not
prevented.

---

## Scenario 5: Physical tampering with the sensors themselves

**Attack:** An attacker covers the PIR sensor's lens, or physically disconnects
a wire, to blind the intrusion detection before attempting entry.

**System response:** None currently. SecureGate has no self-check or
"sensor offline" detection - if the PIR stops reporting motion (whether from
being covered, disconnected, or failing), the system has no way to notice.

**Residual risk:** A more robust version would periodically verify sensor
health (e.g. checking that the PIR's signal isn't permanently stuck LOW for
an implausibly long time) and log a `SENSOR_FAULT` event if so, rather than
silently trusting the sensor is always working.

---

## Summary

These scenarios show SecureGate handling the threats it was explicitly designed
for well (brute force, unauthenticated presence), while having real,
acknowledged gaps in areas outside its current scope (log integrity, sensor
health monitoring, credential management at scale). Documenting the gaps
alongside the successes is intentional - it reflects how the system would
actually need to evolve for a real deployment, not just what was convenient to
build for a portfolio demo.
