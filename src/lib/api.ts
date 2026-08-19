/**
 * Thin typed client for the Clinic Booking API (FastAPI).
 *
 * Base URL comes from VITE_API_URL so the same build can point at a local
 * uvicorn server or the deployed Railway URL. Defaults to localhost:8000.
 */
export const API_URL =
  (import.meta.env["VITE_API_URL"] as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

export type Doctor = {
  id: number;
  name: string;
  specialty: string | null;
  working_hours: { day_of_week: number; start_time: string; end_time: string }[];
};

export type Patient = { id: number; name: string; email: string };

export type Appointment = {
  id: number;
  doctor_id: number;
  patient_id: number;
  slot_start: string;
  slot_end: string;
  status: "booked" | "cancelled";
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string | null;
};

export type Availability = {
  doctor_id: number;
  date: string;
  available_slots: string[];
};

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(
      `Could not reach the API at ${API_URL}. Is uvicorn running?`,
      "NETWORK_ERROR",
      0,
    );
  }

  if (!res.ok) {
    let code = `HTTP_${res.status}`;
    let message = res.statusText;
    try {
      const body = (await res.json()) as {
        error?: string;
        message?: string;
        detail?: unknown;
      };
      code = body.error ?? code;
      message =
        body.message ??
        (typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail)) ??
        message;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, code, res.status);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  doctors: () => request<Doctor[]>("/doctors"),
  patients: () => request<Patient[]>("/patients"),
  availability: (doctorId: number, date: string) =>
    request<Availability>(`/doctors/${doctorId}/availability?date=${date}`),
  book: (body: { doctor_id: number; patient_id: number; slot_start: string }) =>
    request<Appointment>("/appointments", { method: "POST", body: JSON.stringify(body) }),
  cancel: (id: number, reason: string) =>
    request<Appointment>(`/appointments/${id}/cancel`, {
      method: "PATCH",
      body: JSON.stringify({ reason }),
    }),
  reschedule: (id: number, slotStart: string) =>
    request<Appointment>(`/appointments/${id}/reschedule`, {
      method: "PATCH",
      body: JSON.stringify({ slot_start: slotStart }),
    }),
  patientAppointments: (patientId: number) =>
    request<Appointment[]>(`/patients/${patientId}/appointments`),
};

/** 2026-08-20 in the browser's local date, used for the date input default. */
export function todayISO(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

export function formatSlot(iso: string) {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}

export function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString([], {
    weekday: "short",
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  });
}
