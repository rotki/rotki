import type { EvmSwapEvent, SwapSubEventModel } from '@/types/history/events';
import type { ComputedRef, Ref } from 'vue';
import { DateFormat } from '@/types/date-format';
import { convertFromTimestamp, convertToTimestamp } from '@/utils/date';
import dayjs from 'dayjs';

export function useDateTime<T extends { timestamp: number }>(states: Ref<T>): ComputedRef<string> {
  return computed<string>({
    get() {
      return convertFromTimestamp(get(states, 'timestamp'), DateFormat.DateMonthYearHourMinuteSecond, true);
    },
    set(value?: string) {
      const timestamp = !value
        ? dayjs().valueOf()
        : convertToTimestamp(value, DateFormat.DateMonthYearHourMinuteSecond, true);
      set(states, { ...get(states), timestamp });
    },
  });
}

export function toSubEvent(event: EvmSwapEvent): Required<SwapSubEventModel> {
  return {
    amount: event.amount.toString(),
    asset: event.asset,
    identifier: event.identifier,
    locationLabel: event.locationLabel ?? '',
    userNotes: event.userNotes ?? '',
  };
}
