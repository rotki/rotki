import { startPromise } from '@shared/utils';
import { get, set } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, readonly, type Ref, ref, shallowRef, toValue, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import {
  BUCKET_TRACE_PAGE_SIZE,
  useBucketTraceApi,
} from '@/modules/history/reconciliation/api/use-bucket-trace-api';
import {
  type BucketTraceResponse,
  type BucketTraceRow,
  type InspectedBucket,
  namedReconciliationFailure,
} from '@/modules/history/reconciliation/schemas';

type PageDirection = 'earlier' | 'more';

interface UseBucketTraceReturn {
  earlierCount: ComputedRef<number>;
  error: Readonly<Ref<unknown>>;
  hasEarlier: ComputedRef<boolean>;
  hasMore: ComputedRef<boolean>;
  loading: Readonly<Ref<boolean>>;
  loadingEarlier: Readonly<Ref<boolean>>;
  loadingMore: Readonly<Ref<boolean>>;
  loadMoreError: Readonly<Ref<unknown>>;
  rows: ComputedRef<BucketTraceRow[]>;
  shownFrom: ComputedRef<number>;
  shownTo: ComputedRef<number>;
  trace: ComputedRef<BucketTraceResponse | undefined>;
  loadEarlier: () => void;
  loadMore: () => void;
  retryInitial: () => void;
  retryPage: () => void;
}

/**
 * Loads and paginates the chronological event trace for the inspected bucket.
 *
 * @remarks
 * Closing the drawer or switching targets bumps `requestSeq` so in-flight responses are dropped.
 * Initial loads omit `offset` so the backend can center blocked buckets around their stop; when
 * that yields a non-zero initial offset, `loadEarlier` prepends the omitted prefix while
 * `loadMore` appends later pages. Page-load errors stay separate from `error` so loaded rows
 * remain visible.
 */
export function useBucketTrace(
  open: MaybeRefOrGetter<boolean>,
  target: MaybeRefOrGetter<InspectedBucket | undefined>,
): UseBucketTraceReturn {
  const { t } = useI18n({ useScope: 'global' });

  const loading = shallowRef<boolean>(false);
  const loadingMore = shallowRef<boolean>(false);
  const loadingEarlier = shallowRef<boolean>(false);
  const error = shallowRef<unknown>();
  const loadMoreError = shallowRef<unknown>();
  const trace = shallowRef<BucketTraceResponse>();
  const rows = ref<BucketTraceRow[]>([]);
  const firstOffset = shallowRef<number>(0);
  let requestSeq = 0;
  let lastPageDirection: PageDirection = 'more';

  const { fetchBucketTrace } = useBucketTraceApi();

  const earlierCount = computed<number>(() => get(firstOffset));
  const hasEarlier = computed<boolean>(() => get(firstOffset) > 0);
  const hasMore = computed<boolean>(() => {
    const current = get(trace);
    return !!current && get(firstOffset) + get(rows).length < current.pagination.total;
  });
  const shownFrom = computed<number>(() => get(firstOffset) + 1);
  const shownTo = computed<number>(() => get(firstOffset) + get(rows).length);

  function namedFailure(failure: unknown): unknown {
    return namedReconciliationFailure(failure, t('data_issues.reconciliation.failure.unexpected_response'));
  }

  function isBusy(): boolean {
    return get(loading) || get(loadingMore) || get(loadingEarlier);
  }

  function pageRange(direction: PageDirection): { limit: number; offset: number } | undefined {
    if (direction === 'earlier') {
      if (!get(hasEarlier))
        return undefined;
      const offset = Math.max(0, get(firstOffset) - BUCKET_TRACE_PAGE_SIZE);
      return { limit: get(firstOffset) - offset, offset };
    }
    if (!get(hasMore))
      return undefined;
    return { limit: BUCKET_TRACE_PAGE_SIZE, offset: get(firstOffset) + get(rows).length };
  }

  function setPageLoading(direction: PageDirection, value: boolean): void {
    set(direction === 'earlier' ? loadingEarlier : loadingMore, value);
  }

  function applyPageResponse(direction: PageDirection, response: BucketTraceResponse): void {
    set(trace, response);
    if (direction === 'earlier') {
      set(rows, [...response.rows, ...get(rows)]);
      set(firstOffset, response.pagination.offset);
      return;
    }
    set(rows, [...get(rows), ...response.rows]);
  }

  function canFetchPage(direction: PageDirection): { current: InspectedBucket; range: { limit: number; offset: number } } | undefined {
    const current = toValue(target);
    const range = pageRange(direction);
    if (!current || !get(trace) || !range || isBusy())
      return undefined;
    return { current, range };
  }

  async function fetchInitial(): Promise<void> {
    const current = toValue(target);
    if (!current)
      return;

    const seq = ++requestSeq;
    set(loading, true);
    set(loadingMore, false);
    set(loadingEarlier, false);
    set(error, undefined);
    set(loadMoreError, undefined);

    try {
      const response = await fetchBucketTrace({
        asset: current.bucket.asset,
        limit: BUCKET_TRACE_PAGE_SIZE,
        location: current.account.location,
        locationLabel: current.account.locationLabel,
        protocol: current.bucket.protocol,
      });
      if (seq !== requestSeq)
        return;
      set(trace, response);
      set(rows, response.rows);
      set(firstOffset, response.pagination.offset);
    }
    catch (error_: unknown) {
      if (seq !== requestSeq || isRequestCancellation(error_))
        return;
      set(error, namedFailure(error_));
    }
    finally {
      if (seq === requestSeq)
        set(loading, false);
    }
  }

  async function fetchPage(direction: PageDirection): Promise<void> {
    const request = canFetchPage(direction);
    if (!request)
      return;

    const seq = ++requestSeq;
    lastPageDirection = direction;
    setPageLoading(direction, true);
    set(loadMoreError, undefined);

    try {
      const response = await fetchBucketTrace({
        asset: request.current.bucket.asset,
        limit: request.range.limit,
        location: request.current.account.location,
        locationLabel: request.current.account.locationLabel,
        offset: request.range.offset,
        protocol: request.current.bucket.protocol,
      });
      if (seq === requestSeq)
        applyPageResponse(direction, response);
    }
    catch (error_: unknown) {
      if (seq === requestSeq && !isRequestCancellation(error_))
        set(loadMoreError, namedFailure(error_));
    }
    finally {
      if (seq === requestSeq)
        setPageLoading(direction, false);
    }
  }

  function loadMore(): void {
    startPromise(fetchPage('more'));
  }

  function loadEarlier(): void {
    startPromise(fetchPage('earlier'));
  }

  function retryInitial(): void {
    startPromise(fetchInitial());
  }

  function retryPage(): void {
    startPromise(fetchPage(lastPageDirection));
  }

  watch(
    [(): boolean => toValue(open), (): InspectedBucket | undefined => toValue(target)],
    ([isOpen, current]) => {
      if (!isOpen || !current) {
        requestSeq += 1;
        set(loading, false);
        set(loadingMore, false);
        set(loadingEarlier, false);
        return;
      }
      set(trace, undefined);
      set(rows, []);
      set(firstOffset, 0);
      set(error, undefined);
      set(loadMoreError, undefined);
      startPromise(fetchInitial());
    },
    { immediate: true },
  );

  return {
    earlierCount,
    error: readonly(error),
    hasEarlier,
    hasMore,
    loadEarlier,
    loading: readonly(loading),
    loadingEarlier: readonly(loadingEarlier),
    loadingMore: readonly(loadingMore),
    loadMore,
    loadMoreError: readonly(loadMoreError),
    retryInitial,
    retryPage,
    rows: computed<BucketTraceRow[]>(() => get(rows)),
    shownFrom,
    shownTo,
    trace: computed<BucketTraceResponse | undefined>(() => get(trace)),
  };
}
