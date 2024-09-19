import dayjs from 'dayjs';
import { type Notification, Severity } from '@rotki/common';
import type { CalendarEventPayload } from '@/types/history/calendar';
import type { CommonMessageHandler } from '@/types/websocket-messages';

export function useCalendarReminderHandler(t: ReturnType<typeof useI18n>['t']): CommonMessageHandler<CalendarEventPayload> {
  const { getChainName } = useSupportedChains();
  const { addressNameSelector } = useAddressesNamesStore();
  const router = useRouter();

  const handle = (data: CalendarEventPayload): Notification => {
    const { name, timestamp } = data;
    const now = dayjs();
    const eventTime = dayjs(timestamp * 1000);
    const isEventTime = now.isSameOrAfter(eventTime);

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

    return {
      title,
      message,
      display: true,
      severity: Severity.REMINDER,
      action: {
        label: t('notification_messages.reminder.open_calendar'),
        persist: true,
        action: async (): Promise<void> => {
          await router.push({
            path: '/calendar',
            query: { timestamp: timestamp.toString() },
          });
        },
      },
    };
  };

  return { handle };
};
