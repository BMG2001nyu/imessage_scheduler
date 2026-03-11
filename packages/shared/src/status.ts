export enum MessageStatus {
  QUEUED = "QUEUED",
  ACCEPTED = "ACCEPTED",
  SENT = "SENT",
  DELIVERED = "DELIVERED",
  FAILED = "FAILED",
  CANCELLED = "CANCELLED",
}

export const MESSAGE_STATUS_LABELS: Record<MessageStatus, string> = {
  [MessageStatus.QUEUED]: "Queued",
  [MessageStatus.ACCEPTED]: "Sending",
  [MessageStatus.SENT]: "Sent",
  [MessageStatus.DELIVERED]: "Delivered",
  [MessageStatus.FAILED]: "Failed",
  [MessageStatus.CANCELLED]: "Cancelled",
};

export const MESSAGE_STATUS_COLORS: Record<MessageStatus, string> = {
  [MessageStatus.QUEUED]: "bg-blue-100 text-blue-700",
  [MessageStatus.ACCEPTED]: "bg-amber-100 text-amber-700",
  [MessageStatus.SENT]: "bg-green-100 text-green-700",
  [MessageStatus.DELIVERED]: "bg-emerald-100 text-emerald-700",
  [MessageStatus.FAILED]: "bg-red-100 text-red-700",
  [MessageStatus.CANCELLED]: "bg-gray-100 text-gray-500",
};
