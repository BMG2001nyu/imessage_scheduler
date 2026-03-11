"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Send, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { COMMON_TIMEZONES, guessTimezone } from "@/lib/timezones";
import { showToast } from "./toast";

const formSchema = z.object({
  phone_number: z
    .string()
    .min(2, "Phone number is required")
    .refine(
      (v) => /^\+[1-9]\d{1,14}$/.test(v.replace(/[\s()\-.]/g, "")),
      { message: "Enter a valid phone number (e.g. +1 555 123 4567)" }
    ),
  body: z
    .string()
    .min(1, "Message cannot be empty")
    .max(5000, "Message is too long (max 5,000 chars)"),
  scheduled_at: z.string().min(1, "Schedule time is required"),
  timezone: z.string().min(1),
});

type FormData = z.infer<typeof formSchema>;

interface Props {
  onCreated: () => void;
}

export function ScheduleForm({ onCreated }: Props) {
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      phone_number: "",
      body: "",
      scheduled_at: "",
      timezone: guessTimezone(),
    },
  });

  const bodyValue = watch("body");

  const onSubmit = async (data: FormData) => {
    setSubmitting(true);
    try {
      const phone = data.phone_number.replace(/[\s()\-.]/g, "");
      await api.createMessage({
        phone_number: phone,
        body: data.body,
        scheduled_at: new Date(data.scheduled_at).toISOString(),
        timezone: data.timezone,
      });
      showToast("Message scheduled successfully", "success");
      reset();
      onCreated();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to schedule message";
      showToast(message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-card rounded-2xl shadow-sm border border-border p-6 animate-fade-in">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <div>
          <label htmlFor="phone" className="block text-sm font-medium text-foreground mb-1.5">
            Phone Number
          </label>
          <input
            id="phone"
            type="tel"
            placeholder="+1 (555) 000-0000"
            autoComplete="tel"
            className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground placeholder:text-muted transition-all"
            {...register("phone_number")}
          />
          {errors.phone_number && (
            <p className="mt-1.5 text-sm text-red-500">{errors.phone_number.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="body" className="block text-sm font-medium text-foreground mb-1.5">
            Message
          </label>
          <textarea
            id="body"
            rows={4}
            placeholder="Enter your message here..."
            className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground placeholder:text-muted resize-none transition-all"
            {...register("body")}
          />
          <div className="flex justify-between mt-1">
            {errors.body ? (
              <p className="text-sm text-red-500">{errors.body.message}</p>
            ) : (
              <span />
            )}
            <span className="text-xs text-muted tabular-nums">
              {bodyValue?.length || 0} / 5,000
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label htmlFor="scheduled_at" className="block text-sm font-medium text-foreground mb-1.5">
              Scheduled Date & Time
            </label>
            <input
              id="scheduled_at"
              type="datetime-local"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground transition-all"
              {...register("scheduled_at")}
            />
            {errors.scheduled_at && (
              <p className="mt-1.5 text-sm text-red-500">{errors.scheduled_at.message}</p>
            )}
          </div>

          <div>
            <label htmlFor="timezone" className="block text-sm font-medium text-foreground mb-1.5">
              Timezone
            </label>
            <select
              id="timezone"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground transition-all"
              {...register("timezone")}
            >
              {COMMON_TIMEZONES.map((tz) => (
                <option key={tz.value} value={tz.value}>
                  {tz.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3 rounded-xl font-medium text-white transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed hover:shadow-lg hover:brightness-110 active:scale-[0.99]"
          style={{
            background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
          }}
        >
          {submitting ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Send className="w-5 h-5" />
          )}
          {submitting ? "Scheduling..." : "Schedule Message"}
        </button>
      </form>
    </div>
  );
}
