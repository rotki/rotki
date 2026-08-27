import type { Ref, WritableComputedRef } from 'vue';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { assert, Blockchain, type Eth2ValidatorEntry, type EthStakingCombinedFilter, type EthStakingFilter } from '@rotki/common';
import { EthStakingFilterValueKeys } from '@/modules/staking/eth/use-eth-staking-filter-fields';
import { EthStakingSelectionKeys } from '@/modules/staking/eth/use-eth-staking-selection-fields';
import { isValidStatus } from '@/modules/staking/eth/use-eth-validator-filter';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';

interface UseEthStakingSelectionReturn {
  modelMatches: WritableComputedRef<MatchedKeywordWithBehaviour<string>>;
}

/** A bar value is a plain string or list here: neither selection field allows exclusion. */
function toList(value: unknown): string[] {
  if (typeof value === 'string')
    return [value];

  if (Array.isArray(value)) {
    assert(value.every(entry => typeof entry === 'string'));
    return value;
  }

  return [];
}

/** Whose staking is shown, as the bar's keys. An empty axis contributes no key at all. */
function toSelectionMatches(model: EthStakingFilter): MatchedKeywordWithBehaviour<string> {
  const validators = 'validators' in model ? model.validators : [];
  if (validators.length > 0)
    return { [EthStakingSelectionKeys.VALIDATOR]: validators.map(validator => validator.index.toString()) };

  const accounts = 'accounts' in model ? model.accounts : [];
  if (accounts.length > 0)
    return { [EthStakingSelectionKeys.WITHDRAWAL_ADDRESS]: accounts.map(account => account.address) };

  return {};
}

/** The period and status, as the bar's keys. */
function toFilterMatches(combined: EthStakingCombinedFilter | undefined): MatchedKeywordWithBehaviour<string> {
  return {
    ...(combined?.fromTimestamp ? { [EthStakingFilterValueKeys.START]: combined.fromTimestamp.toString() } : {}),
    ...(combined?.toTimestamp ? { [EthStakingFilterValueKeys.END]: combined.toTimestamp.toString() } : {}),
    ...(combined?.status ? { [EthStakingFilterValueKeys.STATUS]: combined.status } : {}),
  };
}

/**
 * Bridges the staking page's two models and the flat keyword bag the pill bar speaks.
 *
 * The page holds `EthStakingFilter` (whose staking to show) and `EthStakingCombinedFilter` (over
 * what period, in which status), and the premium component reads both. The bar knows neither, so
 * this is where the two forms meet.
 *
 * Three rules the shapes force, each of them a way this can silently go wrong:
 *
 * 1. **An absent filter is an absent key.** `{ key: undefined }` is not `{}` to the bar's
 *    round-trip guard, and a bag that carries undefined keys makes a newly added pill vanish the
 *    moment it is added.
 * 2. **The selection is a union with no empty member.** There is no "neither validators nor
 *    accounts", so clearing the last pill has to land somewhere: it lands on `{ validators: [] }`,
 *    which is the state the page starts in. Never `undefined` — the component branches on
 *    `'accounts' in filter`.
 * 3. **A validator index must survive a store that has not loaded.** The pill carries the index,
 *    the model wants the whole entry, and the entries arrive asynchronously. Resolving straight
 *    from the store would empty the selection whenever the two are out of step, so entries already
 *    seen are remembered and a value is only dropped when nothing knows it.
 */
export function useEthStakingSelection(
  selection: Ref<EthStakingFilter>,
  filter: Ref<EthStakingCombinedFilter | undefined>,
): UseEthStakingSelectionReturn {
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());

  const known = new Map<string, Eth2ValidatorEntry>();

  function remember(entries: Eth2ValidatorEntry[]): void {
    for (const entry of entries) known.set(entry.index.toString(), entry);
  }

  watchImmediate(ethStakingValidators, entries => remember(entries));
  watchImmediate(selection, model => remember('validators' in model ? model.validators : []));

  const modelMatches = computed<MatchedKeywordWithBehaviour<string>>({
    get() {
      return {
        ...toSelectionMatches(get(selection)),
        ...toFilterMatches(get(filter)),
      };
    },
    set(value) {
      const fromTimestamp = value[EthStakingFilterValueKeys.START];
      const toTimestamp = value[EthStakingFilterValueKeys.END];
      const status = value[EthStakingFilterValueKeys.STATUS];

      assert(typeof fromTimestamp === 'string' || fromTimestamp === undefined);
      assert(typeof toTimestamp === 'string' || toTimestamp === undefined);
      assert((typeof status === 'string' && isValidStatus(status)) || status === undefined);

      set(filter, {
        fromTimestamp: fromTimestamp ? Number(fromTimestamp) : undefined,
        status,
        toTimestamp: toTimestamp ? Number(toTimestamp) : undefined,
      });

      const indices = toList(value[EthStakingSelectionKeys.VALIDATOR]);
      const addresses = toList(value[EthStakingSelectionKeys.WITHDRAWAL_ADDRESS]);

      const namesNoValidator = indices.length === 0;
      if (namesNoValidator && addresses.length > 0) {
        set(selection, { accounts: addresses.map(address => ({ address, chain: Blockchain.ETH })) });
        return;
      }

      const validators = indices
        .map(index => known.get(index))
        .filter((entry): entry is Eth2ValidatorEntry => !!entry);

      set(selection, { validators });
    },
  });

  return { modelMatches };
}
