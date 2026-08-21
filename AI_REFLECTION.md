# Section 4 — AI Reflection

## 1. What did I use AI for across the four sections?

- **Section 1 (design):** as a sounding board. I described the scenario and my
  model sketch, then asked it to argue against a stored `Slot` table. It helped
  me articulate the read-time-derivation trade-off I'd already leaned toward,
  and to phrase the growth path (cached/materialised slots) rather than hand-wave it.
- **Section 2 (implementation):** boilerplate acceleration — Pydantic schemas,
  repository method signatures, FastAPI wiring, and the first draft of the test
  suite. I also used it to enumerate edge cases I might have skipped
  (off-grid `slot_start`, doctor with no working hours for a weekday,
  reschedule onto the appointment's own current slot).
- **Section 3 (deploy/CI):** the GitHub Actions YAML skeleton and Railway
  environment-variable checklist. AI's better than I am at remembering the
  exact conditional syntax (`if: github.event_name == 'push' && github.ref
  == ...`), so I leaned on it for that instead of looking it up myself.
- **Section 4:** only this formatting. The content is mine.

## 2. One example where AI improved my work

I prompted roughly: *"I have a partial unique index on (doctor_id, slot_start)
where status='booked'. My service checks availability, then inserts. Write a
test that proves the double-booking guard actually holds under concurrency —
not a sequential test."*

It suggested a real two-thread test using a barrier so both threads attempt the
insert at the same moment, asserting exactly one 201 and one 409. That's now
`backend/tests/test_concurrency.py`. My own instinct had been to write a
sequential "book twice" test, which would have passed even against a broken
implementation that relied only on the application-level pre-check — it would
have confirmed the code ran without ever proving the property that actually
matters. The barrier-based version is what closes that gap.

## 3. One example where AI output was wrong or incomplete

The first draft it produced stored datetimes with `DateTime(timezone=True)` and
assumed SQLite would round-trip the timezone. It doesn't — SQLite silently drops
`tzinfo` on read-back, so a freshly booked slot's stored datetime no longer
compared equal to the timezone-aware datetime the availability query was
excluding it against. The slot appeared available again immediately after booking.

I caught it because a reschedule test failed with two datetimes that printed
identically but weren't equal. The fix is mine: a custom `UTCDateTime`
SQLAlchemy type (`backend/app/core/types.py`) that normalises to naive UTC on
write and re-attaches `timezone.utc` on read, so SQLite and Postgres behave
identically. AI also initially proposed a plain unique constraint on
`(doctor_id, slot_start)`, which would have permanently blocked rebooking a
cancelled slot — I changed it to a partial index.

## 4. Two decisions I made without AI

1. **Slots are derived at read time, not stored in a `Slot` table.** AI kept
   nudging toward a pre-generated slots table because that's the pattern most
   tutorials show. I trusted my own judgment because the real cost here is
   drift: a slots table plus working hours means two sources of truth and a
   background job to keep them aligned, for a clinic with five doctors. The
   computation is trivially cheap at this scale, and I can add caching later
   without changing the data model.
2. **Reschedule updates the existing row instead of cancel + recreate.** AI's
   suggestion was to cancel the old appointment and insert a new one, which
   reads cleanly but creates a window where the appointment exists in neither
   state (and complicates history/identity). A single `UPDATE` makes freeing the
   old slot and claiming the new one atomic by construction, and the same
   partial unique index still guards the new slot. That's a correctness call I
   was more confident about than the model was.

**Where I deliberately didn't lean on AI:** the ambiguity calls documented in
the README (inclusive working-hours boundaries, missing working hours meaning
"not working", strict grid alignment). Those are product decisions, not code
decisions, and the assessment asks for *my* reasoning.