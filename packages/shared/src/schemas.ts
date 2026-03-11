import { z } from "zod";
import { MessageStatus } from "./status";

export const messageCreateSchema = z.object({
  phone_number: z
    .string()
    .min(2, "Phone number is required")
    .max(20)
    .transform((v) => v.replace(/[\s()\-.]/g, ""))
    .refine((v) => /^\+[1-9]\d{1,14}$/.test(v), {
      message: "Enter a valid phone number (e.g. +1 555 123 4567)",
    }),
  body: z
    .string()
    .min(1, "Message cannot be empty")
    .max(5000, "Message is too long"),
  scheduled_at: z.string().min(1, "Schedule time is required"),
  timezone: z.string().default("UTC"),
});

export const messageUpdateSchema = messageCreateSchema.partial();

export const messageSchema = z.object({
  id: z.string().uuid(),
  phone_number: z.string(),
  body: z.string(),
  scheduled_at: z.string(),
  timezone: z.string(),
  status: z.nativeEnum(MessageStatus),
  created_at: z.string(),
  updated_at: z.string(),
  accepted_at: z.string().nullable().optional(),
  sent_at: z.string().nullable().optional(),
  delivered_at: z.string().nullable().optional(),
  failed_at: z.string().nullable().optional(),
  failure_reason: z.string().nullable().optional(),
  attempts: z.number(),
  max_attempts: z.number(),
  gateway_message_id: z.string().nullable().optional(),
});

export type MessageCreate = z.input<typeof messageCreateSchema>;
export type MessageUpdate = z.input<typeof messageUpdateSchema>;
export type Message = z.infer<typeof messageSchema>;

export interface Stats {
  queued: number;
  accepted: number;
  sent: number;
  delivered: number;
  failed: number;
  cancelled: number;
  total: number;
}

export interface WebSocketEvent {
  event: string;
  data: Message;
}
