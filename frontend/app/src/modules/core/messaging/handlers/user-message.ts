import type { NotificationHandler } from '../interfaces';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { MESSAGE_WARNING, type UserMessageData } from '../types/base';
import { createNotificationHandler } from '../utils/handler-factories';

/**
 * Renders a backend `add_error` / `add_warning` user message.
 *
 * @remarks
 * The lane never interrupts. Each message carries its family (`key`), `subject` and `fields`,
 * but nothing here reads them yet, so a popup cannot say anything the drawer does not say
 * better. The bulk of the corpus is self-describing as ignorable ("Ignoring it", "Skipping
 * balance result", "Check logs for details and open a bug report"), and a condition that does
 * warrant an interrupt earns it by getting a structured `WSMessageType`, not by being a longer
 * string. `Priority.BULK` is what keeps the lane silent: raise it and every backend call site
 * toasts again.
 */
export function createUserMessageHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<UserMessageData> {
  return createNotificationHandler<UserMessageData>(({ value, verbosity }) => ({
    category: NotificationCategory.DEFAULT,
    message: value,
    priority: Priority.BULK,
    severity: verbosity === MESSAGE_WARNING ? Severity.WARNING : Severity.ERROR,
    title: verbosity === MESSAGE_WARNING
      ? t('notification_messages.backend.warning_title')
      : t('notification_messages.backend.title'),
  }));
}
