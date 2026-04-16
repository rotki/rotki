import { type Notification, type NotificationData, Severity } from '@rotki/common';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useNotificationDispatcher } from './use-notification-dispatcher';

export { getErrorMessage } from '@/modules/core/common/logging/error-handling';

interface ToastOptions {
  readonly display?: boolean;
}

interface UseNotificationsReturn {
  /**
   * Send a raw notification with full control over all fields (action, group, category, priority, etc.).
   * Use this for advanced patterns that the convenience methods don't cover.
   */
  notify: (notification: Notification) => void;
  /** Show an error toast notification (displayed by default). */
  notifyError: (title: string, message: string, options?: ToastOptions) => void;
  /** Show a warning toast notification (displayed by default). */
  notifyWarning: (title: string, message: string, options?: ToastOptions) => void;
  /** Show an info toast notification (displayed by default). */
  notifyInfo: (title: string, message: string, options?: ToastOptions) => void;
  /** Remove the first notification matching the predicate. */
  removeMatching: (predicate: (n: NotificationData) => boolean) => void;
  /**
   * Show a success message dialog.
   * When called with two args: `showSuccessMessage(title, description)`.
   * When called with one arg: `showSuccessMessage(description)` — title is auto-generated.
   */
  showSuccessMessage: (title: string, description?: string) => void;
  /**
   * Show an error message dialog.
   * When called with two args: `showErrorMessage(title, description)`.
   * When called with one arg: `showErrorMessage(description)` — title is auto-generated.
   */
  showErrorMessage: (title: string, description?: string) => void;
}

export function useNotifications(): UseNotificationsReturn {
  const { removeMatching: storeRemoveMatching } = useNotificationsStore();
  const { notify: dispatchNotify } = useNotificationDispatcher();
  const { setMessage } = useMessageStore();

  function toast(severity: Severity, title: string, message: string, options?: ToastOptions): void {
    dispatchNotify({
      display: options?.display ?? true,
      message,
      severity,
      title,
    });
  }

  function notify(notification: Notification): void {
    dispatchNotify(notification);
  }

  function notifyError(title: string, message: string, options?: ToastOptions): void {
    toast(Severity.ERROR, title, message, options);
  }

  function notifyWarning(title: string, message: string, options?: ToastOptions): void {
    toast(Severity.WARNING, title, message, options);
  }

  function notifyInfo(title: string, message: string, options?: ToastOptions): void {
    toast(Severity.INFO, title, message, options);
  }

  function removeMatching(predicate: (n: NotificationData) => boolean): void {
    storeRemoveMatching(predicate);
  }

  function showSuccessMessage(title: string, description?: string): void {
    setMessage({ description: description ?? title, success: true, ...(description ? { title } : {}) });
  }

  function showErrorMessage(title: string, description?: string): void {
    setMessage({ description: description ?? title, success: false, ...(description ? { title } : {}) });
  }

  return { notify, notifyError, notifyInfo, notifyWarning, removeMatching, showErrorMessage, showSuccessMessage };
}
