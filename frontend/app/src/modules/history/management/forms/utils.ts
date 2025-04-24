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
