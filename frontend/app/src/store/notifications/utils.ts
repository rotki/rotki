import store from '@/store/store';
import { NotificationBase, NotificationData, Severity } from '@/typing/types';

export const toNotification = (
  message: string,
  severity: Severity,
  id: number,
  title: string = ''
): NotificationData => ({
  title: title,
  message: message,
  severity: severity,
  display: false,
  duration: 5000,
  id: id,
  date: new Date()
});

export const emptyNotification = () => toNotification('', Severity.INFO, 0);

export function notify(
  message: string,
  title: string = '',
  severity: Severity = Severity.ERROR
) {
  store.dispatch('notifications/notify', {
    title,
    message,
    severity
  } as NotificationBase);
}
