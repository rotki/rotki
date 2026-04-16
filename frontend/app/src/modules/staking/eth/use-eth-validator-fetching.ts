import { Blockchain, Eth2Validators, type EthValidatorFilter } from '@rotki/common';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { createValidatorAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

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
  const { runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });

  async function fetchEthStakingValidators(payload?: EthValidatorFilter): Promise<void> {
    if (!isEth2Enabled())
      return;

    const outcome = await runTask<Eth2Validators, { title: string }>(
      async () => getEth2Validators(payload),
      { type: TaskType.FETCH_ETH2_VALIDATORS, meta: { title: t('actions.get_accounts.task.title', { blockchain: Blockchain.ETH2 }) } },
    );

    if (outcome.success) {
      const validators = Eth2Validators.parse(outcome.result);
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
    }
    else if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.get_accounts.error.title'),
        t('actions.get_accounts.error.description', {
          blockchain: Blockchain.ETH2,
          message: outcome.message,
        }),
      );
    }
  }

  return { fetchEthStakingValidators };
}
