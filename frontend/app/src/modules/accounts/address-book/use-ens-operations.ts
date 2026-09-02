import type { AddressBookSimplePayload, EthNames } from '@/modules/accounts/address-book/eth-names';
import { isValidEthAddress } from '@rotki/common';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useAddressesNamesApi } from '@/modules/accounts/address-book/use-addresses-names-api';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseEnsOperationsReturn {
  fetchEnsNames: (payload: AddressBookSimplePayload[], forceUpdate?: boolean) => Promise<void>;
  resolveEnsToAddress: (ensName: string) => Promise<string | null>;
}

export function useEnsOperations(): UseEnsOperationsReturn {
  const { submitTask } = useNativeTask();
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
      const outcome = await submitTask<EthNames>({
        id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.ENS),
        kind: ActivityKind.ACCOUNTS,
        rerunnable: true,
        run: async ({ runTask }): Promise<Result<EthNames, TaskError>> => mapResult(
          await runTask<EthNames>(
            async () => getEnsNamesTask(filteredAddresses),
          ),
          value => value,
        ),
        subtitle: activityLabel(ActivityKind.ACCOUNTS, ActivityPart.ENS, { count: filteredAddresses.length }, filteredAddresses.length),
        title: t('task_center.group.accounts'),
      });

      if (isErr(outcome)) {
        if (isActionable(outcome.error))
          notifyError(t('ens_names.task.title'), t('ens_names.error.message', { message: outcome.error.message }));
      }
      else {
        newResult = outcome.value;
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
