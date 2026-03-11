const STATUS_CONFIG: Record<string, { label: string; classes: string }> = {
  QUEUED: { label: "Queued", classes: "bg-blue-100 text-blue-700" },
  ACCEPTED: { label: "Sending", classes: "bg-amber-100 text-amber-700 animate-pulse-soft" },
  SENT: { label: "Sent", classes: "bg-green-100 text-green-700" },
  DELIVERED: { label: "Delivered", classes: "bg-emerald-100 text-emerald-700" },
  FAILED: { label: "Failed", classes: "bg-red-100 text-red-700" },
  CANCELLED: { label: "Cancelled", classes: "bg-gray-100 text-gray-500" },
};

interface Props {
  status: string;
}

export function StatusBadge({ status }: Props) {
  const config = STATUS_CONFIG[status] || {
    label: status,
    classes: "bg-gray-100 text-gray-600",
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold transition-all ${config.classes}`}
    >
      {config.label}
    </span>
  );
}
