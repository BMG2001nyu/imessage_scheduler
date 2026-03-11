"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { X, Loader2, Save } from "lucide-react";
import type { Message } from "@/lib/api";
import { api } from "@/lib/api";
import { COMMON_TIMEZONES } from "@/lib/timezones";
import { showToast } from "./toast";

const editSchema = z.object({
  phone_number: z
    .string()
    .min(2, "Phone number is required")
    .refine(
      (v) => /^\+[1-9]\d{1,14}$/.test(v.replace(/[\s()\-.]/g, "")),
      { message: "Enter a valid phone number" }
    ),
  body: z.string().min(1, "Message cannot be empty").max(5000),
  scheduled_at: z.string().min(1, "Schedule time is required"),
  timezone: z.string().min(1),
});

type EditData = z.infer<typeof editSchema>;

interface Props {
  message: Message;
  onClose: () => void;
  onSaved: () => void;
}

export function EditModal({ message, onClose, onSaved }: Props) {
  const [submitting, setSubmitting] = useState(false);

  const scheduledLocal = new Date(message.scheduled_at).toISOString().slice(0, 16);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<EditData>({
    resolver: zodResolver(editSchema),
    defaultValues: {
      phone_number: message.phone_number,
      body: message.body,
      scheduled_at: scheduledLocal,
      timezone: message.timezone,
    },
  });

  const onSubmit = async (data: EditData) => {
    setSubmitting(true);
    try {
      await api.updateMessage(message.id, {
        phone_number: data.phone_number.replace(/[\s()\-.]/g, ""),
        body: data.body,
        scheduled_at: new Date(data.scheduled_at).toISOString(),
        timezone: data.timezone,
      });
      onSaved();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update";
      showToast(msg, "error");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-card rounded-2xl shadow-xl border border-border w-full max-w-lg mx-4 p-6 animate-fade-in">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold">Edit Message</h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer">
            <X className="w-5 h-5 text-muted" />
          </button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Phone Number</label>
            <input
              type="tel"
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground transition-all"
              {...register("phone_number")}
            />
            {errors.phone_number && (
              <p className="mt-1 text-sm text-red-500">{errors.phone_number.message}</p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium mb-1">Message</label>
            <textarea
              rows={3}
              className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground resize-none transition-all"
              {...register("body")}
            />
            {errors.body && (
              <p className="mt-1 text-sm text-red-500">{errors.body.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium mb-1">Date & Time</label>
              <input
                type="datetime-local"
                className="w-full px-4 py-2.5 rounded-xl border border-border bg-white text-foreground transition-all"
                {...register("scheduled_at")}
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Timezone</label>
              <select
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

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 rounded-xl border border-border font-medium text-muted hover:bg-gray-50 transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 py-2.5 rounded-xl font-medium text-white flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 hover:shadow-lg hover:brightness-110 active:scale-[0.99]"
              style={{
                background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
              }}
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {submitting ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
