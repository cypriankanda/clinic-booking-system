import { createFileRoute } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import {
  Activity,
  CalendarDays,
  Clock,
  Loader2,
  RefreshCw,
  Stethoscope,
  UserRound,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  api,
  ApiError,
  API_URL,
  formatDateTime,
  formatSlot,
  todayISO,
  type Appointment,
} from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Clinic Booking — Book a 30-minute doctor slot" },
      {
        name: "description",
        content:
          "Browse live doctor availability, book a 30-minute appointment, then cancel or reschedule it. Frontend for the Clinic Booking REST API.",
      },
      { property: "og:title", content: "Clinic Booking  Book a 30-minute doctor slot" },
      {
        property: "og:description",
        content:
          "Live doctor availability, instant booking, cancel and reschedule  powered by the Clinic Booking API.",
      },
    ],
  }),
  component: Index,
});

function ApiStatus() {
  const { data, isError, isPending } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: false,
    refetchInterval: 30_000,
  });

  const state = isPending ? "checking" : isError ? "down" : data?.status === "ok" ? "up" : "down";

  return (
    <div className="flex items-center gap-2 text-xs text-primary-foreground/80">
      <span
        className={`inline-block size-2 rounded-full ${
          state === "up" ? "bg-success" : state === "down" ? "bg-destructive" : "bg-accent"
        }`}
      />
      <span className="font-mono">
        {state === "up" ? "API online" : state === "down" ? "API unreachable" : "checking…"} ·{" "}
        {API_URL}
      </span>
    </div>
  );
}

function Index() {
  const queryClient = useQueryClient();
  const [doctorId, setDoctorId] = useState<string>("");
  const [patientId, setPatientId] = useState<string>("");
  const [date, setDate] = useState<string>(todayISO());
  const [cancelTarget, setCancelTarget] = useState<Appointment | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [rescheduleTarget, setRescheduleTarget] = useState<Appointment | null>(null);

  const doctors = useQuery({ queryKey: ["doctors"], queryFn: api.doctors, retry: false });
  const patients = useQuery({ queryKey: ["patients"], queryFn: api.patients, retry: false });

  useEffect(() => {
    if (!doctorId && doctors.data?.[0]) setDoctorId(String(doctors.data[0].id));
  }, [doctors.data, doctorId]);
  useEffect(() => {
    if (!patientId && patients.data?.[0]) setPatientId(String(patients.data[0].id));
  }, [patients.data, patientId]);

  const availability = useQuery({
    queryKey: ["availability", doctorId, date],
    queryFn: () => api.availability(Number(doctorId), date),
    enabled: Boolean(doctorId && date),
    retry: false,
  });

  const appointments = useQuery({
    queryKey: ["appointments", patientId],
    queryFn: () => api.patientAppointments(Number(patientId)),
    enabled: Boolean(patientId),
    retry: false,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["availability"] });
    queryClient.invalidateQueries({ queryKey: ["appointments"] });
  };

  const onError = (error: unknown) => {
    const e = error as ApiError;
    toast.error(e.code ?? "Request failed", { description: e.message });
  };

  const book = useMutation({
    mutationFn: (slotStart: string) =>
      api.book({
        doctor_id: Number(doctorId),
        patient_id: Number(patientId),
        slot_start: slotStart,
      }),
    onSuccess: (appt) => {
      toast.success("Appointment booked", { description: formatDateTime(appt.slot_start) });
      invalidate();
    },
    onError,
  });

  const cancel = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => api.cancel(id, reason),
    onSuccess: () => {
      toast.success("Appointment cancelled");
      setCancelTarget(null);
      setCancelReason("");
      invalidate();
    },
    onError,
  });

  const reschedule = useMutation({
    mutationFn: ({ id, slotStart }: { id: number; slotStart: string }) =>
      api.reschedule(id, slotStart),
    onSuccess: (appt) => {
      toast.success("Appointment moved", { description: formatDateTime(appt.slot_start) });
      setRescheduleTarget(null);
      invalidate();
    },
    onError,
  });

  const doctorName = (id: number) => doctors.data?.find((d) => d.id === id)?.name ?? `#${id}`;
  const selectedDoctor = doctors.data?.find((d) => String(d.id) === doctorId);
  const apiDown = doctors.isError;

  return (
    <main className="min-h-screen bg-background">
      <header className="bg-gradient-clinic">
        <div className="mx-auto flex max-w-5xl flex-col gap-4 px-5 py-10 sm:px-8">
          <div className="flex items-center gap-2 text-primary-foreground/85">
            <Activity className="size-5" />
            <span className="font-mono text-xs uppercase tracking-[0.2em]">Clinic Booking API</span>
          </div>
          <h1 className="max-w-2xl text-3xl font-semibold text-primary-foreground sm:text-4xl">
            Five doctors. Thirty-minute slots. No double bookings.
          </h1>
          <p className="max-w-xl text-sm text-primary-foreground/85">
            Availability is computed live from each doctor&apos;s working hours, minus what&apos;s
            already booked  with a one-hour minimum notice applied.
          </p>
          <ApiStatus />
        </div>
      </header>

      <div className="mx-auto max-w-5xl px-5 py-10 sm:px-8">
        {apiDown && (
          <div className="mb-8 rounded-xl border border-destructive/30 bg-destructive/5 p-5">
            <h2 className="text-base font-semibold text-foreground">API not reachable</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Start the backend, then reload: <code className="font-mono">uvicorn app.main:app --reload</code>{" "}
              inside <code className="font-mono">backend/</code>. Current target:{" "}
              <code className="font-mono">{API_URL}</code> (override with{" "}
              <code className="font-mono">VITE_API_URL</code>).
            </p>
          </div>
        )}

        <section className="rounded-2xl border border-border bg-card p-5 shadow-card sm:p-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <Stethoscope className="size-4 text-muted-foreground" /> Doctor
              </Label>
              <Select value={doctorId} onValueChange={setDoctorId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a doctor" />
                </SelectTrigger>
                <SelectContent>
                  {doctors.data?.map((d) => (
                    <SelectItem key={d.id} value={String(d.id)}>
                      {d.name}
                      {d.specialty ? ` · ${d.specialty}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label className="flex items-center gap-2">
                <UserRound className="size-4 text-muted-foreground" /> Patient
              </Label>
              <Select value={patientId} onValueChange={setPatientId}>
                <SelectTrigger>
                  <SelectValue placeholder="Select a patient" />
                </SelectTrigger>
                <SelectContent>
                  {patients.data?.map((p) => (
                    <SelectItem key={p.id} value={String(p.id)}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="date" className="flex items-center gap-2">
                <CalendarDays className="size-4 text-muted-foreground" /> Date
              </Label>
              <Input
                id="date"
                type="date"
                value={date}
                min={todayISO()}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
          </div>

          {selectedDoctor?.working_hours[0] && (
            <p className="mt-4 text-xs text-muted-foreground">
              Works {selectedDoctor.working_hours.length} day
              {selectedDoctor.working_hours.length > 1 ? "s" : ""} a week,{" "}
              {selectedDoctor.working_hours[0]!.start_time.slice(0, 5)}–
              {selectedDoctor.working_hours[0]!.end_time.slice(0, 5)} UTC.
            </p>
          )}
        </section>

        <section className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Available slots</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => availability.refetch()}
              disabled={availability.isFetching}
            >
              <RefreshCw className={`size-4 ${availability.isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          {availability.isPending && doctorId ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" /> Loading availability…
            </div>
          ) : availability.data && availability.data.available_slots.length > 0 ? (
            <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-7">
              {availability.data.available_slots.map((slot) => (
                <Button
                  key={slot}
                  variant="outline"
                  className="font-mono transition-shadow hover:shadow-lift"
                  disabled={book.isPending || !patientId}
                  onClick={() => book.mutate(slot)}
                >
                  {formatSlot(slot)}
                </Button>
              ))}
            </div>
          ) : (
            <p className="rounded-xl border border-dashed border-border bg-surface p-6 text-sm text-muted-foreground">
              No free slots for this doctor on {date}. Weekends and fully booked days show up empty,
              and slots inside the next hour are hidden.
            </p>
          )}
          <p className="mt-3 text-xs text-muted-foreground">All times shown in UTC.</p>
        </section>

        <section className="mt-10">
          <h2 className="mb-4 text-lg font-semibold">Upcoming appointments</h2>
          {appointments.data && appointments.data.length > 0 ? (
            <ul className="space-y-3">
              {appointments.data.map((appt) => (
                <li
                  key={appt.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-card p-4 shadow-card"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <Clock className="size-4 text-muted-foreground" />
                      <span className="font-mono text-sm">{formatDateTime(appt.slot_start)}</span>
                      <Badge variant={appt.status === "booked" ? "default" : "secondary"}>
                        {appt.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {doctorName(appt.doctor_id)} · appointment #{appt.id}
                    </p>
                  </div>
                  {appt.status === "booked" && (
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setDoctorId(String(appt.doctor_id));
                          setRescheduleTarget(appt);
                        }}
                      >
                        <RefreshCw className="size-4" /> Reschedule
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setCancelTarget(appt)}
                      >
                        <XCircle className="size-4" /> Cancel
                      </Button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="rounded-xl border border-dashed border-border bg-surface p-6 text-sm text-muted-foreground">
              Nothing booked yet for this patient.
            </p>
          )}
        </section>
      </div>

      {/* Cancel dialog */}
      <Dialog open={Boolean(cancelTarget)} onOpenChange={(o) => !o && setCancelTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Cancel appointment</DialogTitle>
            <DialogDescription>
              {cancelTarget && formatDateTime(cancelTarget.slot_start)} — the slot becomes bookable
              again immediately.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor="reason">Reason</Label>
            <Textarea
              id="reason"
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Patient is unwell / schedule clash…"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setCancelTarget(null)}>
              Keep it
            </Button>
            <Button
              variant="destructive"
              disabled={cancelReason.trim().length === 0 || cancel.isPending}
              onClick={() =>
                cancelTarget &&
                cancel.mutate({ id: cancelTarget.id, reason: cancelReason.trim() })
              }
            >
              {cancel.isPending && <Loader2 className="size-4 animate-spin" />}
              Cancel appointment
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reschedule dialog */}
      <Dialog
        open={Boolean(rescheduleTarget)}
        onOpenChange={(o) => !o && setRescheduleTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Move appointment #{rescheduleTarget?.id}</DialogTitle>
            <DialogDescription>
              Pick a new slot for {rescheduleTarget && doctorName(rescheduleTarget.doctor_id)} on{" "}
              {date}. Change the date above to look at another day.
            </DialogDescription>
          </DialogHeader>
          <div className="grid max-h-64 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4">
            {availability.data?.available_slots.length ? (
              availability.data.available_slots.map((slot) => (
                <Button
                  key={slot}
                  variant="outline"
                  className="font-mono"
                  disabled={reschedule.isPending}
                  onClick={() =>
                    rescheduleTarget &&
                    reschedule.mutate({ id: rescheduleTarget.id, slotStart: slot })
                  }
                >
                  {formatSlot(slot)}
                </Button>
              ))
            ) : (
              <p className="col-span-full text-sm text-muted-foreground">
                No free slots on {date} for this doctor.
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}
