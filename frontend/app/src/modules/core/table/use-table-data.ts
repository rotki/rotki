import type { MaybeRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { FetchError } from 'ofetch';
import { api, RequestCancelledError } from '@/modules/core/api';
import { defaultCollectionState } from '@/modules/core/common/data/collection-utils';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseTableDataReturn<TItem> {
  collection: Ref<Collection<TItem>>;
  isLoading: Ref<boolean>;
  /** The last fetch failure, or `undefined` once a fetch succeeds. Lets a table render inline. */
  error: Ref<unknown>;
  refetch: () => Promise<void>;
}

/**
 * Owns the fetch side of a server table: the async state holding the collection,
 * the error reporting, and the optional cancellation of in-flight requests.
 *
 * `requestPayload` is taken as a getter so the payload can be assembled after this
 * composable is created; it is only read when a fetch actually happens.
 */
interface FetchFailure {
  code: string;
  message: string;
  path: string;
}

/** The message the backend put in the response body, which reads better than the error's own. */
function responseMessage(data: unknown): string | undefined {
  if (typeof data !== 'object' || data === null || !('message' in data))
    return undefined;

  return typeof data.message === 'string' ? data.message : undefined;
}

/** The parts of a failed request the generic error notification needs. */
function describeFetchFailure(error: unknown): FetchFailure {
  const fetchError = error instanceof FetchError ? error : undefined;

  return {
    code: fetchError?.statusCode?.toString() ?? '',
    message: responseMessage(fetchError?.data) ?? getErrorMessage(error),
    path: fetchError?.request?.toString() ?? '',
  };
}

export function useTableData<TItem extends NonNullable<unknown>, TPayload>(
  requestData: (payload: MaybeRef<TPayload>) => Promise<Collection<TItem>>,
  requestPayload: () => MaybeRef<TPayload>,
  cancelTag?: string,
): UseTableDataReturn<TItem> {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const { error, execute, isLoading, state: collection } = useAsyncState<Collection<TItem>, MaybeRef<TPayload>[]>(
    requestData,
    defaultCollectionState<TItem>(),
    {
      delay: 0,
      immediate: false,
      onError(e) {
        if (e instanceof RequestCancelledError)
          return;

        const { code, message, path } = describeFetchFailure(e);

        logger.error(e);
        if (Number(code) >= 400) {
          notifyError(t('error.generic.title'), t('error.generic.message', { code, message, path }));
        }
      },
      resetOnExecute: false,
    },
  );

  /** Hits the api for the current pagination and filter state, cancelling any request in flight. */
  const refetch = async (): Promise<void> => {
    if (cancelTag)
      api.cancelByTag(cancelTag);

    await execute(0, requestPayload());
  };

  return {
    collection,
    error,
    isLoading,
    refetch,
  };
}
