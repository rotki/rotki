import type { DeepReadonly, Ref } from 'vue';
import { type BigNumber, type Eth2ValidatorEntry, type Eth2Validators, type EthStakingCombinedFilter, type EthStakingFilter, Zero } from '@rotki/common';
import { omit } from 'es-toolkit';
import { isEmpty } from 'es-toolkit/compat';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { nonEmptyProperties } from '@/modules/core/common/data/data';
import { logger } from '@/modules/core/common/logging/logging';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

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

  /**
   * The filter whose answer `total` should reflect, as the same string the activity id embeds.
   * Empty means "every validator", which is what a direct {@link setTotal} computes.
   *
   * Filter changes are not serialised, so without this the response that happens to land last wins
   * rather than the one belonging to the newest filter, leaving a total for a filter the user has
   * moved off.
   *
   * Keyed by the filter rather than by the call: the premium component re-emits `update:filter`
   * after every change, so the same filter is requested twice as a matter of course and both
   * answers are equally valid.
   */
  let wantedFilter = '';

  const { queryEth2Validators } = useBlockchainAccountsApi();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

  function applyTotal(validators?: Eth2Validators['entries']): void {
    const publicKeys = validators?.map((validator: Eth2ValidatorEntry) => validator.publicKey);
    const stakingValidators = get(ethStakingValidators);
    const selectedValidators = publicKeys
      ? stakingValidators.filter(validator => publicKeys.includes(validator.publicKey))
      : stakingValidators;
    const totalStakedAmount = selectedValidators.reduce((sum, item) => sum.plus(item.amount), Zero);
    set(total, totalStakedAmount);
  }

  function setTotal(validators?: Eth2Validators['entries']): void {
    // Claims the slot, so a request still in flight cannot land on top of a caller that has just
    // set the total directly (the page refresh does exactly that).
    wantedFilter = '';
    applyTotal(validators);
  }

  /**
   * Recomputes `total` for the filter and selection as they currently stand.
   *
   * @remarks
   * Do not route the query through the task orchestrator. This runs on every filter change and the
   * query behind it is a millisecond-scale database read, so an orchestrated task only adds the
   * polling delay and leaves the total lagging the validator count beside it.
   */
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

    const filterKey = JSON.stringify(combinedFilter);
    wantedFilter = filterKey;

    try {
      const validators = await queryEth2Validators(combinedFilter);
      // Not `setTotal`: this must not claim the slot, it has to check whether the answer it carries
      // is still the one being asked for.
      if (filterKey === wantedFilter)
        applyTotal(validators.entries);
    }
    catch (error: unknown) {
      logger.error(`failed to compute the staked total for ${filterKey}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

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
