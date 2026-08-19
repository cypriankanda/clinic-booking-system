def _future_monday_slot(hour="09:00:00"):
    # 2026-08-24 is a Monday, comfortably in the future relative to when
    # this assessment is being built.
    return f"2026-08-24T{hour}Z"


def test_book_appointment_success(client, seeded_ids):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": _future_monday_slot(),
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "booked"
    assert body["slot_start"] == _future_monday_slot()


def test_double_booking_same_slot_returns_409(client, seeded_ids):
    payload = {
        "doctor_id": seeded_ids["doctor_id"],
        "patient_id": seeded_ids["patient_a_id"],
        "slot_start": _future_monday_slot(),
    }
    r1 = client.post("/appointments", json=payload)
    assert r1.status_code == 201

    payload["patient_id"] = seeded_ids["patient_b_id"]
    r2 = client.post("/appointments", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"] == "CONFLICT"


def test_booking_in_the_past_returns_422(client, seeded_ids):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": "2020-01-01T09:00:00Z",
        },
    )
    assert r.status_code == 422


def test_booking_outside_working_hours_returns_422(client, seeded_ids):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": _future_monday_slot("20:00:00"),
        },
    )
    assert r.status_code == 422


def test_booking_misaligned_slot_returns_422(client, seeded_ids):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": _future_monday_slot("09:15:00"),
        },
    )
    assert r.status_code == 422


def test_booking_unknown_doctor_returns_404(client, seeded_ids):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": 99999,
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": _future_monday_slot(),
        },
    )
    assert r.status_code == 404


def test_booking_unknown_patient_returns_404(client, seeded_ids):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": 99999,
            "slot_start": _future_monday_slot(),
        },
    )
    assert r.status_code == 404


def test_booking_within_one_hour_notice_returns_422(client, seeded_ids):
    from datetime import datetime, timedelta, timezone

    near = (datetime.now(timezone.utc) + timedelta(minutes=20)).replace(
        second=0, microsecond=0
    )
    # round down to the nearest 30-minute boundary so this fails on the
    # notice rule specifically, not slot alignment
    near = near.replace(minute=(near.minute // 30) * 30)

    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": near.isoformat().replace("+00:00", "Z"),
        },
    )
    assert r.status_code == 422


def test_availability_excludes_booked_slot(client, seeded_ids):
    client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_a_id"],
            "slot_start": _future_monday_slot(),
        },
    )
    r = client.get(f"/doctors/{seeded_ids['doctor_id']}/availability?date=2026-08-24")
    assert r.status_code == 200
    assert _future_monday_slot() not in r.json()["available_slots"]
    assert _future_monday_slot("09:30:00") in r.json()["available_slots"]


def test_availability_unknown_doctor_returns_404(client, seeded_ids):
    r = client.get("/doctors/99999/availability?date=2026-08-24")
    assert r.status_code == 404


def test_availability_bad_date_returns_422(client, seeded_ids):
    r = client.get(f"/doctors/{seeded_ids['doctor_id']}/availability?date=not-a-date")
    assert r.status_code == 422
