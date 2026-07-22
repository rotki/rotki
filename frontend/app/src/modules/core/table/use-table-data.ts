import type { FetchError } from 'ofetch';
import type { MaybeRef, Ref } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import { api, RequestCancelledError } from '@/modules/core/api';
import { defaultCollectionState } from '@/modules/core/common/data/collection-utils';
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

        const error = e as FetchError<{ message: string }>;
        const path = error.request?.toString() ?? '';
        const code = error.statusCode?.toString() ?? '';
        const message = (error.data as { message?: string } | undefined)?.message ?? error.message ?? '';

        logger.error(error);
        if (Number(code) >= 400) {
          notifyError(t('error.generic.title'), t('error.generic.message', { code, message, path }));
        }
      },
      resetOnExecute: false,
    },
  );

  /**
   * Hits the api to fetch data based on pagination/filter changes
   * @returns {Promise<void>}
   */
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
