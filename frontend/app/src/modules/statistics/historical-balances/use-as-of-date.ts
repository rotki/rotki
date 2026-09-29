import type { DeepReadonly, Ref, WritableComputedRef } from 'vue';
import { startPromise } from '@shared/utils';
import dayjs from 'dayjs';
import { asOfTimestamp, type DateKey, parseDateKey, toDateKey } from '@/modules/statistics/historical-balances/as-of-date';

const QUERY_KEY = 'date';

function nowSeconds(): number {
  return dayjs().unix();
}

interface UseAsOfDateReturn {
  /** The chosen day, read from and written to the route query. Today when the query has none. */
  modelDay: WritableComputedRef<DateKey>;
  /** The as-of time for the chosen day, in unix seconds. */
  timestamp: DeepReadonly<Ref<number>>;
  /**
   * Re-reads the as-of time against the current time.
   *
   * @returns whether it moved; only today's can, since today ends now
   */
  restamp: () => boolean;
}

/**
 * The historical balances page's as-of day, kept in the route query so the page is linkable.
 *
 * @remarks
 * The timestamp is taken when the day is chosen rather than tracking the clock: today's as-of
 * time is now, and following the clock would reload the balances every time it ticked.
 */
export function useAsOfDate(): UseAsOfDateReturn {
  const route = useRoute();
  const router = useRouter();

  const modelDay = computed<DateKey>({
    get: () => parseDateKey(route.query[QUERY_KEY]) ?? toDateKey(nowSeconds()),
    set: (day: DateKey) => {
      startPromise(router.replace({ query: { ...route.query, [QUERY_KEY]: day } }));
    },
  });

  const timestamp = ref<number>(asOfTimestamp(get(modelDay), nowSeconds()));

  function restamp(): boolean {
    const next = asOfTimestamp(get(modelDay), nowSeconds());
    if (next === get(timestamp))
      return false;
    set(timestamp, next);
    return true;
  }

  watch(modelDay, restamp);

  return { modelDay, restamp, timestamp: readonly(timestamp) };
}
