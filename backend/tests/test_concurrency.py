"""
Proves the actual requirement from the assessment: "Once booked, that slot
must not be available to others" -- under real concurrent requests, not just
sequential ones.

Each thread gets its own DB session (bound to the same on-disk SQLite file,
so they share state) and its own BookingService instance, mirroring how two
simultaneous HTTP requests would each get their own request-scoped session
in production. We bypass the TestClient/HTTP layer here to guarantee true
overlap of the two attempts -- Starlette's TestClient does not reliably
run requests in parallel.
"""
import threading

from app.exceptions import ConflictError
from app.services.booking_service import BookingService

SLOT = "2026-08-24T09:00:00Z"


def test_concurrent_bookings_of_the_same_slot_only_one_succeeds(SessionLocal, seeded_ids):
    from datetime import datetime

    slot_start = datetime.fromisoformat(SLOT.replace("Z", "+00:00"))

    results = {"success": 0, "conflict": 0, "other_error": []}
    lock = threading.Lock()
    start_barrier = threading.Barrier(2)

    def attempt(patient_key: str):
        db = SessionLocal()
        try:
            service = BookingService(db)
            start_barrier.wait()  # line both threads up to hit the DB together
            try:
                service.book_appointment(
                    doctor_id=seeded_ids["doctor_id"],
                    patient_id=seeded_ids[patient_key],
                    slot_start=slot_start,
                )
                with lock:
                    results["success"] += 1
            except ConflictError:
                with lock:
                    results["conflict"] += 1
            except Exception as e:  # noqa: BLE001
                with lock:
                    results["other_error"].append(repr(e))
        finally:
            db.close()

    t1 = threading.Thread(target=attempt, args=("patient_a_id",))
    t2 = threading.Thread(target=attempt, args=("patient_b_id",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["other_error"] == []
    assert results["success"] == 1, "Exactly one concurrent booking attempt should succeed"
    assert results["conflict"] == 1, "The losing attempt should get a clean ConflictError"
