import store from '@/store/store';
import { NotificationData, Severity } from '@/typing/types';

export const toNotification = (
  message: string,
  severity: Severity,
  id: number,
  title: string = ''
): NotificationData => ({
  title: title,
  message: message,
  severity: severity,
  id: id
});

export function notify(
  message: string,
  title: string = '',
  severity: Severity = Severity.ERROR
) {
  const id = store.getters['notifications/nextId'] as number;
  const notification = toNotification(message, severity, id, title);
  store.commit('notifications/update', [notification]);
}
