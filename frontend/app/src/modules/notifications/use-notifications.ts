import { Severity } from '@rotki/common';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';

export { getErrorMessage } from '@/utils/error-handling';

interface ToastOptions {
  readonly display?: boolean;
}

interface UseNotificationsReturn {
  notifyError: (title: string, message: string, options?: ToastOptions) => void;
  notifyWarning: (title: string, message: string, options?: ToastOptions) => void;
  notifyInfo: (title: string, message: string, options?: ToastOptions) => void;
  showSuccessMessage: (title: string, description: string) => void;
  showErrorMessage: (title: string, description: string) => void;
}

export function useNotifications(): UseNotificationsReturn {
  const { notify } = useNotificationsStore();
  const { setMessage } = useMessageStore();

  function toast(severity: Severity, title: string, message: string, options?: ToastOptions): void {
    notify({
      display: options?.display ?? true,
      message,
      severity,
      title,
    });
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

  function showSuccessMessage(title: string, description: string): void {
    setMessage({ description, success: true, title });
  }

  function showErrorMessage(title: string, description: string): void {
    setMessage({ description, success: false, title });
  }

  return { notifyError, notifyInfo, notifyWarning, showErrorMessage, showSuccessMessage };
}
