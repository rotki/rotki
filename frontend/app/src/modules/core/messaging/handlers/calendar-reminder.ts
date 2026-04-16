import type { NotificationHandler } from '../interfaces';
import type { CalendarEventWithReminder } from '@/modules/calendar/types';
import { NotificationCategory, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import dayjs from 'dayjs';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useCalendarReminderApi } from '@/modules/calendar/use-calendar-reminder-api';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { createNotificationHandler } from '@/modules/core/messaging/utils';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

export function createCalendarReminderHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<CalendarEventWithReminder> {
  // Capture all functions and stores at handler creation time (in setup context)
  const { getChainName } = useSupportedChains();
  const { getAddressName } = useAddressNameResolution();
  const { removeMatching } = useNotificationsStore();
  const { editCalendarReminder } = useCalendarReminderApi();

  return createNotificationHandler<CalendarEventWithReminder>((data) => {
    const { address: dataAddress, blockchain, counterparty, description, identifier, name, reminder, timestamp } = data;
    const now = dayjs();
    const eventTime = dayjs(timestamp * 1000);
    const isEventTime = now.isSameOrAfter(eventTime);

    removeMatching(({ category, extras }) => category === NotificationCategory.CALENDAR_REMINDER && (extras?.eventId === identifier));

    let title = name;
    if (!isEventTime) {
      const relativeTime = eventTime.from(now);
      title = `"${name}" ${relativeTime}`;
    }

    let message = '';
    if (dataAddress && blockchain) {
      const address = getAddressName(dataAddress, blockchain) || dataAddress;
      message += `${t('common.account')}: ${address} (${getChainName(blockchain)}) \n`;
    }

    if (counterparty)
      message += `${t('common.counterparty')}: ${counterparty} \n`;

    if (description)
      message += description;

    const acknowledgeReminder = (): void => {
      const payload = {
        ...reminder,
        acknowledged: true,
        eventId: identifier,
      };

      startPromise(editCalendarReminder(payload));
    };

    return {
      action: {
        action: async (): Promise<void> => {
          acknowledgeReminder();
          await router.push({
            path: '/calendar',
            query: { timestamp: timestamp.toString() },
          });
        },
        label: t('notification_messages.reminder.open_calendar'),
      },
      category: NotificationCategory.CALENDAR_REMINDER,
      display: true,
      extras: {
        eventId: identifier,
      },
      message,
      severity: Severity.REMINDER,
      title,
    };
  });
}
