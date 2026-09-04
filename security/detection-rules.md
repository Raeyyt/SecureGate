# SecureGate Detection Rules

This document catalogs the detection logic implemented in SecureGate, in the
format a security operations team might use to document alerting rules. Each
rule lists its trigger condition, the logged event, severity, and the
automated response (if any).

---

## Rule: RFID-001 - Unrecognized card presented

- **Trigger:** A scanned RFID UID does not match the authorized UID stored in
  `authorizedUID[]`.
- **Logged event:** `RFID_AUTH_FAILURE`
- **Severity:** Low (single occurrence) / escalates via ATT-001 if repeated
- **Automated response:** Counts toward the shared failure counter (see
  ATT-001). No PIN prompt is shown - the flow stops immediately.
- **False positive considerations:** A legitimate user's own card failing to
  read cleanly (e.g. held too far from the reader) would also trigger this
  rule. Operators reviewing logs should look for a subsequent successful scan
  within a few seconds as a sign of a misread rather than an actual
  unauthorized attempt.

## Rule: PIN-001 - Incorrect PIN entered

- **Trigger:** An authorized card is scanned successfully, but the PIN entered
  afterward does not match the stored value.
- **Logged event:** `PIN_AUTH_FAILURE`
- **Severity:** Low (single occurrence) / escalates via ATT-001 if repeated
- **Automated response:** Counts toward the shared failure counter.

## Rule: ATT-001 - Brute-force threshold exceeded

- **Trigger:** 3 consecutive failed attempts (any combination of
  `RFID_AUTH_FAILURE` and `PIN_AUTH_FAILURE`) without an intervening
  `ACCESS_GRANTED`.
- **Logged event:** `BRUTE_FORCE_DETECTED`, immediately followed by
  `ACCESS_DENIED` with detail "System locked out"
- **Severity:** High
- **Automated response:** System enters a 30-second lockout. All card scans
  and keypad input are ignored for the duration. Buzzer sounds once per
  second as an audible deterrent/alert. Lockout auto-clears after 30 seconds
  and the failure counter resets to zero.
- **Tuning notes:** Threshold (3) and lockout duration (30s) are both
  configurable constants (`MAX_ATTEMPTS`, `LOCKOUT_DURATION`) in the sketch.
  A production deployment should tune these based on expected false-positive
  rate from legitimate users (e.g. someone genuinely forgetting their PIN)
  versus how much friction is acceptable.

## Rule: PIR-001 - Motion detected

- **Trigger:** The PIR sensor's output pin transitions from LOW to HIGH.
- **Logged event:** `INTRUSION_DETECTED`
- **Severity:** Medium on its own; should be correlated with nearby
  authentication events during review (see below)
- **Automated response:** None automatic beyond logging - this rule is
  intentionally "detect and log" rather than "detect and lock down," since a
  single PIR sensor triggering alone is common (foot traffic, pets, HVAC
  airflow) and treating every trigger as a full alarm would create alert
  fatigue.
- **Correlation guidance:** An `INTRUSION_DETECTED` event with no
  `ACCESS_GRANTED` event in the surrounding time window is more suspicious
  than one that occurs alongside a normal authenticated entry.

## Rule: AUTH-001 - Successful two-factor authentication

- **Trigger:** Authorized card UID matches, followed by correct PIN entry.
- **Logged events:** `RFID_AUTH_SUCCESS`, then `PIN_AUTH_SUCCESS`, then
  `ACCESS_GRANTED`
- **Severity:** Informational
- **Automated response:** Relay energizes for 2 seconds (simulated unlock),
  confirmation beep sounds, failure counter resets to zero.

## Rule: SYS-001 - System boot

- **Trigger:** Arduino powers on or resets.
- **Logged event:** `SYSTEM_START`
- **Severity:** Informational
- **Use case:** Helps distinguish "no events logged because nothing happened"
  from "no events logged because the device was off/reset" during log review.

## Rule: SYS-002 - Lockout period ends

- **Trigger:** 30 seconds elapse since a lockout began.
- **Logged event:** `SYSTEM_RESET`
- **Severity:** Informational
- **Use case:** Marks the boundary of a lockout window in the log, useful when
  reconstructing a timeline of an incident.

---

## Coverage gaps (not currently implemented as rules)

For completeness, these are detection rules a more mature version of
SecureGate would add - listed here so the gap is documented rather than
silently absent:

- **Sensor health check** - no rule currently fires if the PIR sensor stops
  reporting entirely (see `attack-scenarios.md`, Scenario 5).
- **Log tampering detection** - no rule currently fires if `securegate_log.jsonl`
  is modified or deleted outside the normal append-only write pattern.
- **Off-hours access flagging** - the current ruleset treats every successful
  authentication the same regardless of time of day; a real deployment might
  flag `ACCESS_GRANTED` events outside expected hours as worth extra review.
