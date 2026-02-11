import type { Ref } from 'vue';
import type { TaskMeta } from '@/types/task';
import { type BigNumber, type Eth2ValidatorEntry, Eth2Validators, type EthStakingCombinedFilter, type EthStakingFilter, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { useBlockchainAccountsApi } from '@/composables/api/blockchain/accounts';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { nonEmptyProperties } from '@/utils/data';

interface UseEthValidatorManagementReturn {
  fetchValidatorsWithFilter: () => Promise<void>;
  filter: Ref<EthStakingCombinedFilter | undefined>;
  selection: Ref<EthStakingFilter>;
  setTotal: (validators?: Eth2Validators['entries']) => void;
  total: Ref<BigNumber>;
}

export function useEthValidatorManagement(): UseEthValidatorManagementReturn {
  const filter = ref<EthStakingCombinedFilter>();
  const selection = ref<EthStakingFilter>({
    validators: [],
  });
  const total = ref<BigNumber>(Zero);

  const { getEth2Validators } = useBlockchainAccountsApi();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { awaitTask } = useTaskStore();

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
    const filterVal = get(filter);
    const selectionVal = get(selection);
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

    const { taskId } = await getEth2Validators(combinedFilter);
    const taskMeta: TaskMeta = { title: '' };
    const { result } = await awaitTask<Eth2Validators, TaskMeta>(taskId, TaskType.FETCH_ETH2_VALIDATORS, taskMeta);
    const parsed = Eth2Validators.parse(result);
    setTotal(parsed.entries);
  }

  // Watch for filter changes
  watch([selection, filter], async () => {
    await fetchValidatorsWithFilter();
  });

  return {
    fetchValidatorsWithFilter,
    filter,
    selection,
    setTotal,
    total,
  };
}
