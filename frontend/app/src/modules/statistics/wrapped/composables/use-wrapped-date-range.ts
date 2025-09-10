import type { ComputedRef, Ref } from 'vue';
import { get, set } from '@vueuse/shared';
import dayjs from 'dayjs';

interface UseWrappedDateRangeReturn {
  end: Ref<number>;
  getYearRange: (year: number) => { start: number; end: number };
  initializeEndDate: () => void;
  invalidRange: ComputedRef<boolean>;
  setYearRange: (year: number) => void;
  start: Ref<number>;
  startModel: ComputedRef<number | undefined>;
}

export function useWrappedDateRange(): UseWrappedDateRangeReturn {
  const end = ref<number>(0);
  const start = ref<number>(0);

  const startModel = computed<number | undefined>({
    get() {
      return get(start) || undefined;
    },
    set(value: number | undefined) {
      set(start, value || 0);
    },
  });

  const invalidRange = computed<boolean>(
    () =>
      !!get(start)
      && !!get(end) && get(start) > get(end),
  );

  function getYearRange(year: number): { start: number; end: number } {
    return {
      end: dayjs().year(year).endOf('year').unix(),
      start: dayjs().year(year).startOf('year').unix(),
    };
  }

  function setYearRange(year: number): void {
    const range = getYearRange(year);
    set(start, range.start);
    set(end, range.end);
  }

  function initializeEndDate(): void {
    if (!get(end)) {
      set(end, dayjs().unix());
    }
  }

  return {
    end,
    getYearRange,
    initializeEndDate,
    invalidRange,
    setYearRange,
    start,
    startModel,
  };
}
