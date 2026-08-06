import type { DeepReadonly, Ref } from 'vue';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { type BigNumber, type Eth2ValidatorEntry, Eth2Validators, type EthStakingCombinedFilter, type EthStakingFilter, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { map as mapResult, type Result } from 'plainfp/result';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { nonEmptyProperties } from '@/modules/core/common/data/data';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseEthValidatorManagementReturn {
  fetchValidatorsWithFilter: () => Promise<void>;
  modelFilter: Ref<EthStakingCombinedFilter | undefined>;
  modelSelection: Ref<EthStakingFilter>;
  setTotal: (validators?: Eth2Validators['entries']) => void;
  total: DeepReadonly<Ref<BigNumber>>;
}

export function useEthValidatorManagement(): UseEthValidatorManagementReturn {
  const modelFilter = ref<EthStakingCombinedFilter>();
  const modelSelection = ref<EthStakingFilter>({
    validators: [],
  });
  const total = ref<BigNumber>(Zero);

  const { getEth2Validators } = useBlockchainAccountsApi();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  function setTotal(validators?: Eth2Validators['entries']): void {
    const publicKeys = validators?.map((validator: Eth2ValidatorEntry) => validator.publicKey);
    const stakingValidators = get(ethStakingValidators);
    const selectedValidators = publicKeys
      ? stakingValidators.filter(validator => publicKeys.includes(validator.publicKey))
      : stakingValidators;
    const totalStakedAmount = selectedValidators.reduce((sum, item) => sum.plus(item.amount), Zero);
    set(total, totalStakedAmount);
  }

  async function fetchValidatorsWithFilter(): Promise<void> {
    const filterVal = get(modelFilter);
    const selectionVal = get(modelSelection);
    const statusFilter = filterVal ? omit(filterVal, ['fromTimestamp', 'toTimestamp']) : {};
    const accounts
      = 'accounts' in selectionVal
        ? { addresses: selectionVal.accounts.map(account => account.address) }
        : { validatorIndices: selectionVal.validators.map((validator: Eth2ValidatorEntry) => validator.index) };

    const combinedFilter = nonEmptyProperties({ ...statusFilter, ...accounts });

    if (isEmpty(combinedFilter)) {
      setTotal(undefined);
      return;
    }

    // Per-request identity: each distinct filter is its own activity, so concurrent filter changes
    // never dedup onto one promise and clobber each other's `total`. Failures are ignored here as
    // they were before migration — this is a passive totals widget with no error surface.
    await submitTask({
      // A passive totals widget: it re-fires on every filter change and its id embeds the raw
      // filter, so surfacing it would spam the panel with rows indistinguishable from the real
      // validator fetch. Tracked like any activity, never rendered.
      ephemeral: true,
      id: makeActivityId(ActivityKind.STAKING, ActivityPart.VALIDATORS, JSON.stringify(combinedFilter)),
      kind: ActivityKind.STAKING,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<Eth2Validators>(
          async () => getEth2Validators(combinedFilter),
        ),
        (result) => {
          setTotal(Eth2Validators.parse(result).entries);
        },
      ),
      title: t('task_center.group.staking'),
    });
  }

  // Watch for filter changes
  watch([modelSelection, modelFilter], async () => {
    await fetchValidatorsWithFilter();
  });

  return {
    fetchValidatorsWithFilter,
    modelFilter,
    modelSelection,
    setTotal,
    total: readonly(total),
  };
}
