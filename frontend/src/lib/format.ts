import { format, formatDistanceToNow, isPast, differenceInMinutes } from "date-fns";

export function formatPhone(phone: string): string {
  if (phone.startsWith("+1") && phone.length === 12) {
    return `+1 (${phone.slice(2, 5)}) ${phone.slice(5, 8)}-${phone.slice(8)}`;
  }
  return phone;
}

export function formatScheduledTime(dateStr: string): string {
  return format(new Date(dateStr), "MMM d, yyyy 'at' h:mm a");
}

export function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const minutesDiff = Math.abs(differenceInMinutes(new Date(), date));

  if (minutesDiff < 1) return "just now";

  const distance = formatDistanceToNow(date, { addSuffix: true });
  return distance;
}

export function formatUpdatedTime(dateStr: string): string {
  const date = new Date(dateStr);
  const minutesDiff = Math.abs(differenceInMinutes(new Date(), date));

  if (minutesDiff < 60) {
    return formatDistanceToNow(date, { addSuffix: true });
  }
  return format(date, "MMM d, h:mm a");
}

export function isOverdue(dateStr: string): boolean {
  return isPast(new Date(dateStr));
}
