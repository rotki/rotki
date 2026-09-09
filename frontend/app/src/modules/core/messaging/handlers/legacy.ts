import type { NotificationHandler } from '../interfaces';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { type LegacyMessageData, MESSAGE_WARNING } from '../types/base';
import { createNotificationHandler } from '../utils/handler-factories';

/**
 * Renders a bare `add_error` / `add_warning` string from the backend.
 *
 * @remarks
 * The lane never interrupts. It carries no type, group or actionability, so all ~150 backend
 * call sites arrive indistinguishable and a popup cannot say anything the drawer does not say
 * better. The bulk of the corpus is self-describing as ignorable ("Ignoring it", "Skipping
 * balance result", "Check logs for details and open a bug report"), and a condition that does
 * warrant an interrupt earns it by getting a structured `WSMessageType`, not by being a longer
 * string. Omitting `display` leaves `createNotification` to store it silently.
 */
export function createLegacyHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<LegacyMessageData> {
  return createNotificationHandler<LegacyMessageData>(({ value, verbosity }) => ({
    category: NotificationCategory.DEFAULT,
    message: value,
    priority: Priority.BULK,
    severity: verbosity === MESSAGE_WARNING ? Severity.WARNING : Severity.ERROR,
    title: verbosity === MESSAGE_WARNING
      ? t('notification_messages.backend.warning_title')
      : t('notification_messages.backend.title'),
  }));
}
