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
  const modelEnd = shallowRef<number>(0);
  const modelStart = shallowRef<number>(0);

  const startModel = computed<number | undefined>({
    get() {
      return get(modelStart) || undefined;
    },
    set(value: number | undefined) {
      set(modelStart, value ?? 0);
    },
  });

  const invalidRange = computed<boolean>(
    () =>
      !!get(modelStart)
      && !!get(modelEnd) && get(modelStart) > get(modelEnd),
  );

  function getYearRange(year: number): { start: number; end: number } {
    return {
      end: dayjs().year(year).endOf('year').unix(),
      start: dayjs().year(year).startOf('year').unix(),
    };
  }

  function setYearRange(year: number): void {
    const range = getYearRange(year);
    set(modelStart, range.start);
    set(modelEnd, range.end);
  }

  function initializeEndDate(): void {
    if (!get(modelEnd)) {
      set(modelEnd, dayjs().unix());
    }
  }

  return {
    end: modelEnd,
    getYearRange,
    initializeEndDate,
    invalidRange,
    setYearRange,
    start: modelStart,
    startModel,
  };
}
