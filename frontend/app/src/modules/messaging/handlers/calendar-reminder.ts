import type { NotificationHandler } from '../interfaces';
import type { CalendarEventWithReminder } from '@/types/history/calendar';
import { NotificationCategory, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import dayjs from 'dayjs';
import { useCalendarReminderApi } from '@/composables/history/calendar/reminder';
import { useSupportedChains } from '@/composables/info/chains';
import { createNotificationHandler } from '@/modules/messaging/utils';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';

export function createCalendarReminderHandler(t: ReturnType<typeof useI18n>['t'], router: ReturnType<typeof useRouter>): NotificationHandler<CalendarEventWithReminder> {
  return createNotificationHandler<CalendarEventWithReminder>((data) => {
    const { getChainName } = useSupportedChains();
    const { addressNameSelector } = useAddressesNamesStore();
    const { removeMatching } = useNotificationsStore();
    const { editCalendarReminder } = useCalendarReminderApi();

    const { name, timestamp } = data;
    const now = dayjs();
    const eventTime = dayjs(timestamp * 1000);
    const isEventTime = now.isSameOrAfter(eventTime);

    removeMatching(({ category, extras }) => category === NotificationCategory.CALENDAR_REMINDER && (extras?.eventId === data.identifier));

    let title = name;
    if (!isEventTime) {
      const relativeTime = eventTime.from(now);
      title = `"${name}" ${relativeTime}`;
    }

    let message = '';
    if (data.address && data.blockchain) {
      const address = get(addressNameSelector(data.address, data.blockchain)) || data.address;
      message += `${t('common.account')}: ${address} (${get(getChainName(data.blockchain))}) \n`;
    }

    if (data.counterparty)
      message += `${t('common.counterparty')}: ${data.counterparty} \n`;

    if (data.description)
      message += data.description;

    const acknowledgeReminder = (): void => {
      const payload = {
        ...data.reminder,
        acknowledged: true,
        eventId: data.identifier,
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
        eventId: data.identifier,
      },
      message,
      severity: Severity.REMINDER,
      title,
    };
  });
}
