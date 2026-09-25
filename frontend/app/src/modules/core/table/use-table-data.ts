import type { ResultAsync } from 'plainfp/result-async';
import type { MaybeRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { Priority } from '@rotki/common';
import { fromRequest, isRequestFailure, type RequestError, type RequestFailure } from '@/modules/core/api/request-result';
import { api } from '@/modules/core/api/rotki-api';
import { defaultCollectionState } from '@/modules/core/common/data/collection-utils';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

/**
 * Fetches one page of a server table. A failure is carried in the result, never thrown, so the
 * table can show it in place of the rows.
 */
export type TableFetch<TItem, TPayload> = (payload: MaybeRef<TPayload>) => ResultAsync<Collection<TItem>, RequestError>;

export interface UseTableDataReturn<TItem> {
  collection: Readonly<Ref<Collection<TItem>>>;
  isLoading: Readonly<Ref<boolean>>;
  /** The last fetch failure, or `undefined` while a fetch is running or once one succeeds. Lets a table render inline. */
  error: Readonly<Ref<RequestFailure | undefined>>;
  refetch: () => Promise<void>;
}

/**
 * Owns the fetch side of a server table: the collection, the error reporting, and the optional
 * cancellation of in-flight requests.
 *
 * @remarks
 * Only the newest fetch writes its outcome, so an older one settling late cannot overwrite it. A
 * failure empties the collection, because the table shows the reason in its empty state and stale
 * rows would read as the answer to the new request. A cancelled fetch keeps its rows and is never
 * reported. A fetch that throws instead of returning its failure is treated as one.
 *
 * `requestPayload` is taken as a getter so the payload can be assembled after this
 * composable is created; it is only read when a fetch actually happens.
 */
export function useTableData<TItem extends NonNullable<unknown>, TPayload>(
  requestData: TableFetch<TItem, TPayload>,
  requestPayload: () => MaybeRef<TPayload>,
  cancelTag?: string,
): UseTableDataReturn<TItem> {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const collection = shallowRef<Collection<TItem>>(defaultCollectionState<TItem>());
  const isLoading = shallowRef<boolean>(false);
  const error = shallowRef<RequestFailure>();

  let latest = 0;

  function report(failure: RequestFailure): void {
    const { message, path = '', status } = failure;

    logger.error(failure.cause);
    if (status !== undefined && status >= 400) {
      notifyError(
        t('error.generic.title'),
        t('error.generic.message', { code: status.toString(), message, path }),
        { priority: Priority.NORMAL },
      );
    }
  }

  /** Hits the api for the current pagination and filter state, cancelling any request in flight. */
  const refetch = async (): Promise<void> => {
    if (cancelTag)
      api.cancelByTag(cancelTag);

    const run = ++latest;
    set(isLoading, true);
    set(error, undefined);

    const outcome = await fromRequest(async () => requestData(requestPayload()));
    if (run !== latest)
      return;

    set(isLoading, false);

    const result = outcome.ok ? outcome.value : outcome;
    if (result.ok) {
      set(collection, result.value);
      return;
    }

    if (!isRequestFailure(result.error))
      return;

    set(collection, defaultCollectionState<TItem>());
    set(error, result.error);
    report(result.error);
  };

  return {
    collection: shallowReadonly(collection),
    error: shallowReadonly(error),
    isLoading: shallowReadonly(isLoading),
    refetch,
  };
}
