import type { NotificationHandler } from '../interfaces';
import { NotificationCategory, Priority, Severity } from '@rotki/common';
import { parseDeviceLimitError } from '@/modules/auth/create-account/analytics/parse-device-limit-error';
import { createManageDevicesAction } from '@/modules/core/messaging/handlers/premium-status';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { type LegacyMessageData, MESSAGE_WARNING } from '../types/base';
import { createNotificationHandler } from '../utils/handler-factories';

/**
 * Turns a plain backend warning or error into a notification.
 *
 * @remarks
 * A message carrying the device-limit link marker, sent when premium could not start at login,
 * is shown right away with the marker removed and an action to manage the premium devices.
 */
export function createLegacyHandler(t: ReturnType<typeof useI18n>['t']): NotificationHandler<LegacyMessageData> {
  const { openUrl } = useInterop();

  return createNotificationHandler<LegacyMessageData>(({ value, verbosity }) => {
    const { hasLink, parts } = parseDeviceLimitError(value);
    const message = parts.map(part => part.trimEnd()).join('');
    if (hasLink) {
      return {
        action: createManageDevicesAction(t, openUrl),
        category: NotificationCategory.DEFAULT,
        display: true,
        message,
        priority: Priority.BULK,
        severity: Severity.ERROR,
        title: t('notification_messages.premium.inactive.title'),
      };
    }

    return {
      category: NotificationCategory.DEFAULT,
      display: verbosity !== MESSAGE_WARNING,
      message,
      priority: Priority.BULK,
      severity: verbosity === MESSAGE_WARNING ? Severity.WARNING : Severity.ERROR,
      title: verbosity === MESSAGE_WARNING
        ? t('notification_messages.backend.warning_title')
        : t('notification_messages.backend.title'),
    };
  });
}
