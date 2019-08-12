import { NotificationData, Severity } from '@/typing/types';
import store from '@/store/store';

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
  const id = store.getters['notification/nextId']() as number;

  const notification = toNotification(message, severity, id, title);
  store.commit('notifications/update', notification);
}
