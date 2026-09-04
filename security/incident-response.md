# SecureGate Incident Response

This document describes how to respond when SecureGate's detection rules
(see `detection-rules.md`) fire. It's written as a practical runbook - what to
check, in what order, and what a reasonable resolution looks like - rather
than abstract policy.

---

## General approach

For every incident, the log file (`securegate_log.jsonl`) is the primary
source of truth. The dashboard (`python/dashboard/securegate_dashboard.py`) is
the fastest way to review recent activity visually; the raw log is the
fallback for detailed, timestamp-level investigation.

When investigating, always establish a timeline: pull every event within a
few minutes before and after the triggering event, not just the event itself.
Context usually matters more than the single alert.

---

## Incident: BRUTE_FORCE_DETECTED (lockout triggered)

1. **Check the timeline.** Find the 3 failed attempts leading up to the
   lockout. Were they all the same type (e.g. 3 wrong PINs), or a mix
   (wrong card + wrong PIN)? A mix is more consistent with an actual attacker
   probing the system; 3 wrong PINs in a row from otherwise-normal usage is
   more consistent with someone forgetting their PIN.
2. **Check for a UID on the failed attempts.** If `RFID_AUTH_FAILURE` events
   are present, note the UID(s) logged. A UID that's never appeared before is
   more suspicious than the authorized user's own UID paired with wrong PINs
   (which suggests the authorized user just forgot their PIN).
3. **Check what happened after the lockout cleared.** Did a successful
   `ACCESS_GRANTED` follow shortly after (consistent with a legitimate user
   who mistyped, then got it right after the cooldown)? Or did failed
   attempts resume immediately (consistent with a persistent attacker)?
4. **Resolution:**
   - If consistent with legitimate user error: no action needed beyond noting
     it. Consider reminding the user of their PIN through a secure channel.
   - If consistent with an attack attempt: physically inspect the area,
     confirm no unauthorized entry occurred (cross-reference with
     `INTRUSION_DETECTED` events in the same window), and consider whether
     the PIN or authorized card should be rotated.

---

## Incident: INTRUSION_DETECTED with no nearby ACCESS_GRANTED

1. **Confirm it isn't a false trigger.** Check the PIR sensor's physical
   surroundings - airflow from HVAC vents, pets, or sunlight changes are
   common causes of single, isolated motion events with no other activity.
2. **Check event frequency.** A single isolated trigger with nothing else
   around it is lower priority than a cluster of triggers, which is more
   consistent with sustained presence in the monitored area.
3. **Resolution:**
   - Isolated, unexplained trigger: log it as reviewed, no further action
     unless it recurs.
   - Sustained/clustered triggers with no authentication activity: treat as a
     likely tailgating or unauthorized-presence event. Physically inspect the
     area as soon as practical.

---

## Incident: Unexpected SYSTEM_START

An unplanned `SYSTEM_START` (one you weren't expecting - e.g. no power outage,
no intentional reset) can indicate:

- A power interruption (check building/outlet power)
- Someone physically resetting or unplugging the device
- A crash/watchdog reset in the sketch itself

**Resolution:** Check the timestamp against any known power events. If
unexplained, physically inspect the Arduino and wiring for signs of tampering
before assuming it's benign.

---

## Incident: Collector or dashboard not receiving events

This isn't a security event on its own, but it means the monitoring pipeline
has a blind spot, which matters for every other rule in this document.

1. Confirm the Arduino is powered and running (check for the expected boot
   behavior - LCD/Serial output, etc.).
2. Confirm the USB/serial connection between Arduino and PC is intact.
3. Confirm the collector script (`securegate_collector.py`) is running and
   connected to the correct COM port - check its console output for
   "Connected. Logging events to..." versus a connection error.
4. Confirm no other program (e.g. Arduino IDE's Serial Monitor) is holding
   the COM port open, which prevents the collector from connecting.

**Resolution:** Once reconnected, note the gap in coverage in your own
records - any incident that may have occurred during the outage window has no
log evidence and should be treated as an unknown rather than assumed benign.

---

## Post-incident follow-up

For any incident escalated beyond "reviewed, no action needed":

- Note what happened and the resolution in a simple record (even a plain text
  file) outside the automated log, since the automated log itself isn't
  tamper-evident (see `attack-scenarios.md`, Scenario 4).
- If a credential (PIN or card) is suspected compromised, rotate it
  (update `correctPIN` and/or `authorizedUID[]` in the sketch, then
  re-upload).
