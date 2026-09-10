import { type Notification, type NotificationData, Priority, Severity } from '@rotki/common';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useNotificationDispatcher } from './use-notification-dispatcher';

export { getErrorMessage } from '@/modules/core/common/logging/error-handling';

interface ToastOptions {
  /**
   * Classifies the notification, which is what decides whether it interrupts.
   *
   * @remarks
   * `NORMAL` or `BULK` records it in the drawer without a popup; the default pops. Callers say
   * what the notification *is* and the dispatcher decides what to do with it, so there is no way
   * to ask for a popup directly.
   */
  readonly priority?: Priority;
}

interface UseNotificationsReturn {
  /**
   * Send a raw notification with full control over all fields (action, group, category, priority, etc.).
   * Use this for advanced patterns that the convenience methods don't cover.
   */
  notify: (notification: Notification) => void;
  /** Report an error, popped unless `options.priority` classifies it lower. */
  notifyError: (title: string, message: string, options?: ToastOptions) => void;
  /** Report a warning, popped unless `options.priority` classifies it lower. */
  notifyWarning: (title: string, message: string, options?: ToastOptions) => void;
  /** Report an informational outcome, popped unless `options.priority` classifies it lower. */
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

  /**
   * @remarks
   * The fallback is `HIGH` rather than `DEFAULT_PRIORITY` because the two doors into the dispatcher
   * carry opposite assumptions. A caller reaching for `notifyError` and friends is reporting the
   * outcome of something the user just did, so it interrupts unless it says otherwise; a raw
   * `notify()` payload is assembled field by field, so an absent priority there means unclassified
   * and lands on the quiet default instead.
   */
  function toast(severity: Severity, title: string, message: string, options?: ToastOptions): void {
    dispatchNotify({
      message,
      priority: options?.priority ?? Priority.HIGH,
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
