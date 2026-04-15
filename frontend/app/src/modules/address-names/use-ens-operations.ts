import type { AddressBookSimplePayload, EthNames } from '@/modules/address-names/eth-names';
import type { TaskMeta } from '@/modules/tasks/types';
import { isValidEthAddress } from '@rotki/common';
import { useAddressesNamesApi } from '@/composables/api/blockchain/addresses-names';
import { useAddressNameResolution } from '@/modules/address-names/use-address-name-resolution';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';
import { uniqueStrings } from '@/utils/data';
import { logger } from '@/utils/logging';

interface UseEnsOperationsReturn {
  fetchEnsNames: (payload: AddressBookSimplePayload[], forceUpdate?: boolean) => Promise<void>;
  resolveEnsToAddress: (ensName: string) => Promise<string | null>;
}

export function useEnsOperations(): UseEnsOperationsReturn {
  const { runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { updateEnsNamesAndReset } = useAddressNameResolution();
  const { getEnsNames, getEnsNamesTask, resolveEnsNames } = useAddressesNamesApi();

  const fetchEnsNames = async (
    payload: AddressBookSimplePayload[],
    forceUpdate = false,
  ): Promise<void> => {
    if (payload.length === 0)
      return;

    const filteredAddresses = payload
      .map(({ address }) => address)
      .filter(uniqueStrings)
      .filter(isValidEthAddress);

    if (filteredAddresses.length === 0)
      return;

    let newResult: Record<string, string | null> = {};

    if (forceUpdate) {
      const outcome = await runTask<EthNames, TaskMeta>(
        async () => getEnsNamesTask(filteredAddresses),
        { type: TaskType.FETCH_ENS_NAMES, meta: { title: t('ens_names.task.title') } },
      );

      if (outcome.success) {
        newResult = outcome.result;
      }
      else if (isActionableFailure(outcome)) {
        notifyError(t('ens_names.task.title'), t('ens_names.error.message', { message: outcome.message }));
      }
    }
    else {
      newResult = await getEnsNames(filteredAddresses);
    }

    updateEnsNamesAndReset(newResult);
  };

  const resolveEnsToAddress = async (ensName: string): Promise<string | null> => {
    try {
      const address = await resolveEnsNames(ensName);
      if (address && isValidEthAddress(address)) {
        updateEnsNamesAndReset({ [address]: ensName });
        return address;
      }
      return null;
    }
    catch (error: unknown) {
      logger.error(error);
      return null;
    }
  };

  return {
    fetchEnsNames,
    resolveEnsToAddress,
  };
}
