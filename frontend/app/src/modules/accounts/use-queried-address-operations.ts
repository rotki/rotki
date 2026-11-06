import type { QueriedAddressPayload } from '@/modules/session/types';
import { useQueriedAddressApi } from '@/modules/accounts/api/use-queried-address-api';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';

/** Why adding or removing a queried address failed, for the surface that asked to show. */
interface QueriedAddressFailure {
  error: unknown;
}

interface UseQueriedAddressOperationsReturn {
  /** @returns the failure, or nothing once the address was added */
  addQueriedAddress: (payload: QueriedAddressPayload) => Promise<QueriedAddressFailure | undefined>;
  /** @returns the failure, or nothing once the address was removed */
  deleteQueriedAddress: (payload: QueriedAddressPayload) => Promise<QueriedAddressFailure | undefined>;
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

  async function addQueriedAddress(payload: QueriedAddressPayload): Promise<QueriedAddressFailure | undefined> {
    try {
      set(queriedAddresses, await api.addQueriedAddress(payload));
      return undefined;
    }
    catch (error: unknown) {
      return { error };
    }
  }

  async function deleteQueriedAddress(payload: QueriedAddressPayload): Promise<QueriedAddressFailure | undefined> {
    try {
      set(queriedAddresses, await api.deleteQueriedAddress(payload));
      return undefined;
    }
    catch (error: unknown) {
      return { error };
    }
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
