import { SemiPartial } from '@rotki/common/src';
import { Severity } from '@/store/notifications/consts';
import {
  NotificationData,
  NotificationPayload
} from '@/store/notifications/types';
import store from '@/store/store';

export const createNotification = (
  id: number = 0,
  { display, duration, message, severity, title }: NotificationPayload = {
    title: '',
    message: '',
    severity: Severity.INFO
  }
): NotificationData => ({
  title: title,
  message: message,
  severity: severity,
  display: display ?? false,
  duration: duration ?? 5000,
  id: id,
  date: new Date()
});

export const emptyNotification = () => createNotification();

export function notify(
  message: string,
  title: string = '',
  severity: Severity = Severity.ERROR,
  display: boolean = false
) {
  store.dispatch('notifications/notify', {
    title,
    message,
    severity,
    display
  } as NotificationPayload);
}

export async function userNotify(
  options: SemiPartial<NotificationPayload, 'title' | 'message'>
) {
  const defaults: NotificationPayload = {
    title: '',
    message: '',
    severity: Severity.ERROR,
    display: false
  };
  await store.dispatch(
    'notifications/notify',
    Object.assign(defaults, options)
  );
}
