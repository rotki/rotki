import type { CalendarEventWithReminder } from '@/types/history/calendar';
import type { CommonMessageHandler } from '@/types/websocket-messages';
import { useCalendarReminderApi } from '@/composables/history/calendar/reminder';
import { useSupportedChains } from '@/composables/info/chains';
import { useAddressesNamesStore } from '@/store/blockchain/accounts/addresses-names';
import { useNotificationsStore } from '@/store/notifications';
import { type CalendarReminderNotification, NotificationCategory, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import dayjs from 'dayjs';

export function useCalendarReminderHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<CalendarEventWithReminder> {
  const { getChainName } = useSupportedChains();
  const { addressNameSelector } = useAddressesNamesStore();
  const router = useRouter();
  const { prioritized, remove: removeNotification } = useNotificationsStore();
  const { editCalendarReminder } = useCalendarReminderApi();

  const handle = (data: CalendarEventWithReminder): CalendarReminderNotification => {
    const { name, timestamp } = data;
    const now = dayjs();
    const eventTime = dayjs(timestamp * 1000);
    const isEventTime = now.isSameOrAfter(eventTime);

    const existingNotification = prioritized.find(item => item.category === NotificationCategory.CALENDAR_REMINDER && 'eventId' in item && item.eventId === data.identifier);

    if (existingNotification) {
      removeNotification(existingNotification.id);
    }

    let title = name;
    if (!isEventTime) {
      const relativeTime = eventTime.from(now);
      title = `"${name}" ${relativeTime}`;
    }

    let message = '';
    if (data.address && data.blockchain) {
      const address = get(addressNameSelector(data.address)) || data.address;
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
      eventId: data.identifier,
      message,
      severity: Severity.REMINDER,
      title,
    };
  };

  return { handle };
};
