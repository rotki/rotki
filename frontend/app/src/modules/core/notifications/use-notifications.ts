import { type Notification, type NotificationData, NotificationKind, Severity } from '@rotki/common';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';
import { useNotificationDispatcher } from './use-notification-dispatcher';

export { getErrorMessage } from '@/modules/core/common/logging/error-handling';

interface UseNotificationsReturn {
  /**
   * Send a raw notification with full control over all fields (kind, action, group, etc.).
   * Use this for advanced patterns that the convenience methods don't cover.
   */
  notify: (notification: Notification) => void;
  /** Report a failed result of something the user started, which pops. */
  notifyError: (title: string, message: string) => void;
  /** Report a result of something the user started that needs a caveat, which pops. */
  notifyWarning: (title: string, message: string) => void;
  /** Report a result of something the user started, which pops. */
  notifyInfo: (title: string, message: string) => void;
  /**
   * Record a background request that failed with nowhere else to show it, without a popup.
   *
   * @remarks
   * A stopgap: such a failure belongs where the data would have been, and moves there as each
   * surface learns to show its own error.
   */
  notifyFailure: (title: string, message: string) => void;
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
   *
   * @remarks
   * Dropped when no session is live, like every message dialog, unless `options.sessionless` says
   * the error belongs to the logged-out screen (a logout that failed after its session ended).
   */
  showErrorMessage: (title: string, description?: string, options?: ErrorMessageOptions) => void;
}

interface ErrorMessageOptions {
  /** Shows the dialog even with no live session. */
  readonly sessionless?: boolean;
}

export function useNotifications(): UseNotificationsReturn {
  const { removeMatching: storeRemoveMatching } = useNotificationsStore();
  const { notify: dispatchNotify } = useNotificationDispatcher();
  const { setMessage } = useMessageStore();

  function notify(notification: Notification): void {
    dispatchNotify(notification);
  }

  function notifyError(title: string, message: string): void {
    dispatchNotify({ kind: NotificationKind.RESULT, message, severity: Severity.ERROR, title });
  }

  function notifyWarning(title: string, message: string): void {
    dispatchNotify({ kind: NotificationKind.RESULT, message, severity: Severity.WARNING, title });
  }

  function notifyInfo(title: string, message: string): void {
    dispatchNotify({ kind: NotificationKind.RESULT, message, severity: Severity.INFO, title });
  }

  function notifyFailure(title: string, message: string): void {
    dispatchNotify({ kind: NotificationKind.FAILURE, message, severity: Severity.ERROR, title });
  }

  function removeMatching(predicate: (n: NotificationData) => boolean): void {
    storeRemoveMatching(predicate);
  }

  function showSuccessMessage(title: string, description?: string): void {
    setMessage({ description: description ?? title, success: true, ...(description ? { title } : {}) });
  }

  function showErrorMessage(title: string, description?: string, options?: ErrorMessageOptions): void {
    setMessage({ description: description ?? title, success: false, ...(description ? { title } : {}) }, options);
  }

  return { notify, notifyError, notifyFailure, notifyInfo, notifyWarning, removeMatching, showErrorMessage, showSuccessMessage };
}
