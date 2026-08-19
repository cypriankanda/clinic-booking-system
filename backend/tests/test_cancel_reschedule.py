SLOT_A = "2026-08-24T09:00:00Z"
SLOT_B = "2026-08-24T10:00:00Z"


def _book(client, seeded_ids, slot=SLOT_A, patient_key="patient_a_id"):
    r = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids[patient_key],
            "slot_start": slot,
        },
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_cancel_appointment_frees_the_slot(client, seeded_ids):
    appt_id = _book(client, seeded_ids)

    r = client.patch(f"/appointments/{appt_id}/cancel", json={"reason": "Change of plans"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    # Slot should be bookable again by someone else
    r2 = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_b_id"],
            "slot_start": SLOT_A,
        },
    )
    assert r2.status_code == 201


def test_cancel_already_cancelled_returns_409(client, seeded_ids):
    appt_id = _book(client, seeded_ids)
    client.patch(f"/appointments/{appt_id}/cancel", json={"reason": "First cancel"})

    r = client.patch(f"/appointments/{appt_id}/cancel", json={"reason": "Second cancel"})
    assert r.status_code == 409


def test_cancel_unknown_appointment_returns_404(client, seeded_ids):
    r = client.patch("/appointments/99999/cancel", json={"reason": "n/a"})
    assert r.status_code == 404


def test_reschedule_moves_appointment_and_frees_old_slot(client, seeded_ids):
    appt_id = _book(client, seeded_ids, slot=SLOT_A)

    r = client.patch(f"/appointments/{appt_id}/reschedule", json={"slot_start": SLOT_B})
    assert r.status_code == 200
    assert r.json()["slot_start"] == SLOT_B

    # old slot freed
    r2 = client.post(
        "/appointments",
        json={
            "doctor_id": seeded_ids["doctor_id"],
            "patient_id": seeded_ids["patient_b_id"],
            "slot_start": SLOT_A,
        },
    )
    assert r2.status_code == 201


def test_reschedule_into_taken_slot_returns_409(client, seeded_ids):
    _book(client, seeded_ids, slot=SLOT_A, patient_key="patient_a_id")
    appt_b_id = _book(client, seeded_ids, slot=SLOT_B, patient_key="patient_b_id")

    r = client.patch(f"/appointments/{appt_b_id}/reschedule", json={"slot_start": SLOT_A})
    assert r.status_code == 409


def test_reschedule_cancelled_appointment_returns_409(client, seeded_ids):
    appt_id = _book(client, seeded_ids)
    client.patch(f"/appointments/{appt_id}/cancel", json={"reason": "n/a"})

    r = client.patch(f"/appointments/{appt_id}/reschedule", json={"slot_start": SLOT_B})
    assert r.status_code == 409


def test_reschedule_unknown_appointment_returns_404(client, seeded_ids):
    r = client.patch("/appointments/99999/reschedule", json={"slot_start": SLOT_B})
    assert r.status_code == 404
