import type { QueriedAddresses, QueriedAddressPayload } from '@/modules/session/types';
import { map as mapResult, type Result } from 'plainfp/result';
import { fromPromise } from 'plainfp/result-async';
import { useQueriedAddressApi } from '@/modules/accounts/api/use-queried-address-api';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

interface UseQueriedAddressOperationsReturn {
  /** @returns `err` with the request's error, for the caller to name where the user asked */
  addQueriedAddress: (payload: QueriedAddressPayload) => Promise<Result<void, unknown>>;
  /** @returns `err` with the request's error, for the caller to name where the user asked */
  deleteQueriedAddress: (payload: QueriedAddressPayload) => Promise<Result<void, unknown>>;
  fetchQueriedAddresses: () => Promise<void>;
}

/**
 * Reads and edits the addresses each module queries.
 *
 * @remarks
 * Adding and removing are things the user does in a dialog, so their failure is handed back for the
 * dialog to show. Loading runs when a module surface mounts, with nowhere to show it, so its failure
 * pops as a notification.
 */
export function useQueriedAddressOperations(): UseQueriedAddressOperationsReturn {
  const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
  const { notifyError } = useNotifications();
  const api = useQueriedAddressApi();
  const { t } = useI18n({ useScope: 'global' });

  /** Stores the addresses a write answered with, and keeps a failed write's error as the value. */
  async function storeAnswer(request: Promise<QueriedAddresses>): Promise<Result<void, unknown>> {
    return mapResult(await fromPromise(request, (error: unknown) => error), (addresses) => {
      set(queriedAddresses, addresses);
    });
  }

  async function addQueriedAddress(payload: QueriedAddressPayload): Promise<Result<void, unknown>> {
    return storeAnswer(api.addQueriedAddress(payload));
  }

  async function deleteQueriedAddress(payload: QueriedAddressPayload): Promise<Result<void, unknown>> {
    return storeAnswer(api.deleteQueriedAddress(payload));
  }

  async function fetchQueriedAddresses(): Promise<void> {
    try {
      set(queriedAddresses, await api.queriedAddresses());
    }
    catch (error: unknown) {
      notifyError(
        t('queried_address_dialog.title'),
        t('actions.session.fetch_queriable_address.error.message', { message: getErrorMessage(error) }),
      );
    }
  }

  return {
    addQueriedAddress,
    deleteQueriedAddress,
    fetchQueriedAddresses,
  };
}
