import { toast } from "sonner";

import { getErrorMessage } from "./http";

/** Shared `onError` for mutations: surfaces the backend's error message as a toast. */
export function toastMutationError(error: unknown): void {
  toast.error(getErrorMessage(error));
}
