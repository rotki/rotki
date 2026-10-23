import { Blockchain, Eth2Validators, type EthValidatorFilter } from '@rotki/common';
import { map as mapResult, type Result } from 'plainfp/result';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { createValidatorAccount } from '@/modules/accounts/create-account';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { logger } from '@/modules/core/common/logging/logging';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { validatorAddActivity, validatorsActivity } from '@/modules/staking/staking.activity';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { activityLabelOf } from '@/modules/task-center/activity-labels';
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
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  async function fetchEthStakingValidators(payload?: EthValidatorFilter): Promise<void> {
    if (!isEth2Enabled())
      return;

    const outcome = await submitTask({
      id: validatorsActivity.id(),
      kind: validatorsActivity.kind,
      rerunnable: true,
      // A newly added validator belongs in this list; see the matching edge in `use-eth2.ts`.
      staleAfter: [{ kind: validatorAddActivity.kind, parts: validatorAddActivity.partsWithin([]) }],
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<Eth2Validators>(
          async () => getEth2Validators(payload),
        ),
        (result) => {
          const validators = Eth2Validators.parse(result);
          updateAccounts(
            Blockchain.ETH2,
            validators.entries.map(validator => createValidatorAccount(validator, Blockchain.ETH2)),
          );
          set(stakingValidatorsLimits, { limit: validators.entriesLimit, total: validators.entriesFound });
        },
      ),
      subtitle: activityLabelOf(validatorsActivity),
      title: t('task_center.group.staking'),
    });

    onActionableError(outcome, error => logger.error(error.message));
  }

  return { fetchEthStakingValidators };
}
