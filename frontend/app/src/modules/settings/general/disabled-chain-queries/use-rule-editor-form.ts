import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ChainInfo } from '@/modules/core/api/types/chains';
import type { Rule, RuleDraft } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { isValidatorAccount } from '@/modules/accounts/account-utils';

export type RuleKind = 'chain' | 'address';

export type AddressScope = 'all' | 'specific';

export interface AddressOption {
  readonly address: string;
  readonly chainIds: readonly string[];
  readonly searchText: string;
}

export interface UseRuleEditorFormOptions {
  /** All addresses tracked across all chains, keyed by chain. */
  accounts: MaybeRefOrGetter<Record<string, BlockchainAccount[]>>;
  /** All chains the user may pick from. */
  chains: MaybeRefOrGetter<ChainInfo[]>;
  /** Rule being edited, or `undefined` for the create flow. */
  editing: MaybeRefOrGetter<Rule | undefined>;
}

export interface UseRuleEditorFormReturn {
  kind: Ref<RuleKind>;
  chainId: Ref<string | undefined>;
  address: Ref<string | undefined>;
  scope: Ref<AddressScope>;
  selectedChainIds: Ref<string[]>;
  addressOptions: ComputedRef<AddressOption[]>;
  availableChainsForAddress: ComputedRef<string[]>;
  canSave: ComputedRef<boolean>;
  /** Reset the form back to the current `editing` value (or empty/create state). */
  reset: () => void;
  /** Build the draft to emit on save, or `undefined` if the form is not yet valid. */
  buildDraft: () => RuleDraft | undefined;
}

function buildAddressOptions(accounts: Record<string, BlockchainAccount[]>): AddressOption[] {
  const byAddress = new Map<string, Set<string>>();
  for (const [chain, list] of Object.entries(accounts)) {
    for (const account of list) {
      if (isValidatorAccount(account) || account.data.type !== 'address')
        continue;
      const addr = account.data.address;
      const set = byAddress.get(addr);
      if (set === undefined)
        byAddress.set(addr, new Set([chain]));
      else
        set.add(chain);
    }
  }
  const built: AddressOption[] = [];
  for (const [address, chainSet] of byAddress) {
    built.push({
      address,
      chainIds: [...chainSet],
      searchText: address.toLowerCase(),
    });
  }
  built.sort((a, b) => a.address.localeCompare(b.address));
  return built;
}

export function useRuleEditorForm(options: UseRuleEditorFormOptions): UseRuleEditorFormReturn {
  const { accounts, chains, editing } = options;

  // These refs are the form model, bound via v-model from the dialog template.
  // They are intentionally exposed as read-write — the readonly()-on-return lint
  // would break the v-model wiring.
  const kind = shallowRef<RuleKind>('chain');
  const chainId = shallowRef<string>();
  const address = shallowRef<string>();
  const scope = shallowRef<AddressScope>('all');
  const selectedChainIds = ref<string[]>([]);

  const addressOptions = computed<AddressOption[]>(() => buildAddressOptions(toValue(accounts)));

  const availableChainsForAddress = computed<string[]>(() => {
    const target = get(address);
    if (!target)
      return toValue(chains).map(c => c.id);
    return get(addressOptions).find(o => o.address === target)?.chainIds.slice() ?? [];
  });

  const canSave = computed<boolean>(() => {
    if (get(kind) === 'chain')
      return Boolean(get(chainId));
    if (!get(address))
      return false;
    if (get(scope) === 'all')
      return get(availableChainsForAddress).length > 0;
    return get(selectedChainIds).length > 0;
  });

  function reset(): void {
    const current = toValue(editing);
    if (current?.kind === 'chain') {
      set(kind, 'chain');
      set(chainId, current.chainId);
      set(address, undefined);
      set(selectedChainIds, []);
      set(scope, 'all');
      return;
    }
    if (current?.kind === 'address') {
      set(kind, 'address');
      set(chainId, undefined);
      set(address, current.address);
      const available = get(addressOptions).find(o => o.address === current.address)?.chainIds ?? [];
      const isAllChains = available.length > 0
        && current.chainIds.length === available.length
        && available.every(c => current.chainIds.includes(c));
      set(scope, isAllChains ? 'all' : 'specific');
      set(selectedChainIds, [...current.chainIds]);
      return;
    }
    set(kind, 'chain');
    set(chainId, undefined);
    set(address, undefined);
    set(selectedChainIds, []);
    set(scope, 'all');
  }

  function buildDraft(): RuleDraft | undefined {
    if (!get(canSave))
      return undefined;
    if (get(kind) === 'chain') {
      const id = get(chainId);
      if (!id)
        return undefined;
      return { chainId: id, kind: 'chain' };
    }
    const addr = get(address);
    if (!addr)
      return undefined;
    const chainIds = get(scope) === 'all' ? get(availableChainsForAddress) : get(selectedChainIds);
    return { address: addr, chainIds: [...chainIds], kind: 'address' };
  }

  watch(address, () => {
    if (get(kind) !== 'address' || get(scope) !== 'specific')
      return;
    const available = new Set(get(availableChainsForAddress));
    set(selectedChainIds, get(selectedChainIds).filter(c => available.has(c)));
  });

  reset();

  /* eslint-disable @rotki/composable-return-readonly --
   * Form-state refs are exposed read-write because the dialog binds them with v-model.
   */
  return {
    address,
    addressOptions,
    availableChainsForAddress,
    buildDraft,
    canSave,
    chainId,
    kind,
    reset,
    scope,
    selectedChainIds,
  };
  /* eslint-enable @rotki/composable-return-readonly */
}
