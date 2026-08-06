import { Blockchain, Eth2Validators, type EthValidatorFilter } from '@rotki/common';
import { map as mapResult, type Result } from 'plainfp/result';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { createValidatorAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseEthValidatorFetchingReturn {
  fetchEthStakingValidators: (payload?: EthValidatorFilter) => Promise<void>;
}

export function useEthValidatorFetching(): UseEthValidatorFetchingReturn {
  const blockchainValidatorsStore = useBlockchainValidatorsStore();
  const { stakingValidatorsLimits } = storeToRefs(blockchainValidatorsStore);
  const { isEth2Enabled } = blockchainValidatorsStore;

  const { updateAccounts } = useBlockchainAccountsStore();
  const { getEth2Validators } = useBlockchainAccountsApi();
  const { getNativeAsset } = useSupportedChains();
  const { notifyError } = useNotifications();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  async function fetchEthStakingValidators(payload?: EthValidatorFilter): Promise<void> {
    if (!isEth2Enabled())
      return;

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.STAKING, ActivityPart.VALIDATORS),
      kind: ActivityKind.STAKING,
      rerunnable: true,
      // A newly added validator belongs in this list; see the matching edge in `use-eth2.ts`.
      staleAfter: [{ kind: ActivityKind.STAKING, parts: [ActivityPart.ADD] }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<Eth2Validators>(
          async () => getEth2Validators(payload),
        ),
        (result) => {
          const validators = Eth2Validators.parse(result);
          updateAccounts(
            Blockchain.ETH2,
            validators.entries.map(validator =>
              createValidatorAccount(validator, {
                chain: Blockchain.ETH2,
                nativeAsset: getNativeAsset(Blockchain.ETH2),
              }),
            ),
          );
          set(stakingValidatorsLimits, { limit: validators.entriesLimit, total: validators.entriesFound });
        },
      ),
      subtitle: activityLabel(ActivityKind.STAKING, ActivityPart.VALIDATORS),
      title: t('task_center.group.staking'),
    });

    onActionableError(outcome, (error) => {
      logger.error(error.message);
      notifyError(
        t('actions.get_accounts.error.title'),
        t('actions.get_accounts.error.description', {
          blockchain: Blockchain.ETH2,
          message: error.message,
        }),
      );
    });
  }

  return { fetchEthStakingValidators };
}
