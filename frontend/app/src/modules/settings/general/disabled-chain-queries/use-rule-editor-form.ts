import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import type { ChainInfo } from '@/modules/core/api/types/chains';
import type { Rule, RuleDraft } from '@/modules/settings/general/disabled-chain-queries/use-disabled-chain-queries-state';
import { isValidatorAccount } from '@/modules/accounts/account-utils';

type RuleKind = 'chain' | 'address';

type AddressScope = 'all' | 'specific';

interface AddressOption {
  readonly address: string;
  readonly chainIds: readonly string[];
  /** Lowercased haystack: the address plus every name the option is displayed under. */
  readonly searchText: string;
}

export interface UseRuleEditorFormOptions {
  /** All addresses tracked across all chains, keyed by chain. */
  accounts: MaybeRefOrGetter<Record<string, BlockchainAccount[]>>;
  /** All chains the user may pick from. */
  chains: MaybeRefOrGetter<ChainInfo[]>;
  /** Rule being edited, or `undefined` for the create flow. */
  editing: MaybeRefOrGetter<Rule | undefined>;
  /**
   * Resolves the alias name (address book entry or ENS) an address is displayed
   * under, so that the picker can be searched by it and not only by the address.
   */
  resolveName?: (address: string, chainId?: string) => string | undefined;
}

export interface UseRuleEditorFormReturn {
  modelKind: Ref<RuleKind>;
  modelChainId: Ref<string | undefined>;
  modelAddress: Ref<string | undefined>;
  modelScope: Ref<AddressScope>;
  modelSelectedChainIds: Ref<string[]>;
  addressOptions: ComputedRef<AddressOption[]>;
  availableChainsForAddress: ComputedRef<string[]>;
  canSave: ComputedRef<boolean>;
  /** Search predicate for the address picker, matching address, label and alias name. */
  filterAddressOption: (item: AddressOption, query: string) => boolean;
  /** Reset the form back to the current `editing` value (or empty/create state). */
  reset: () => void;
  /** Build the draft to emit on save, or `undefined` if the form is not yet valid. */
  buildDraft: () => RuleDraft | undefined;
}

interface AddressEntry {
  readonly chains: Set<string>;
  readonly labels: Set<string>;
}

function buildAddressOptions(
  accounts: Record<string, BlockchainAccount[]>,
  resolveName?: (address: string, chainId?: string) => string | undefined,
): AddressOption[] {
  const byAddress = new Map<string, AddressEntry>();
  for (const [chain, list] of Object.entries(accounts)) {
    for (const account of list) {
      if (isValidatorAccount(account) || account.data.type !== 'address')
        continue;
      const addr = account.data.address;
      let entry = byAddress.get(addr);
      if (entry === undefined) {
        entry = { chains: new Set(), labels: new Set() };
        byAddress.set(addr, entry);
      }
      entry.chains.add(chain);
      if (account.label)
        entry.labels.add(account.label);
    }
  }
  const built: AddressOption[] = [];
  for (const [address, { chains, labels }] of byAddress) {
    const chainIds = [...chains];
    const aliasName = resolveName?.(address, chainIds[0]);
    const keywords = [address, ...labels];
    if (aliasName)
      keywords.push(aliasName);
    built.push({
      address,
      chainIds,
      searchText: keywords.join(' ').toLowerCase(),
    });
  }
  built.sort((a, b) => a.address.localeCompare(b.address));
  return built;
}

function filterAddressOption(item: AddressOption, query: string): boolean {
  const search = query.trim().toLowerCase();
  if (!search)
    return true;
  return item.searchText.includes(search);
}

export function useRuleEditorForm(options: UseRuleEditorFormOptions): UseRuleEditorFormReturn {
  const { accounts, chains, editing, resolveName } = options;

  // These refs are the form model, bound via v-model from the dialog template.
  // The `model` prefix marks them as writable by the consumer.
  const modelKind = shallowRef<RuleKind>('chain');
  const modelChainId = shallowRef<string>();
  const modelAddress = shallowRef<string>();
  const modelScope = shallowRef<AddressScope>('all');
  const modelSelectedChainIds = ref<string[]>([]);

  const addressOptions = computed<AddressOption[]>(() => buildAddressOptions(toValue(accounts), resolveName));

  const availableChainsForAddress = computed<string[]>(() => {
    const target = get(modelAddress);
    if (!target)
      return toValue(chains).map(c => c.id);
    return get(addressOptions).find(o => o.address === target)?.chainIds.slice() ?? [];
  });

  const canSave = computed<boolean>(() => {
    if (get(modelKind) === 'chain')
      return Boolean(get(modelChainId));
    if (!get(modelAddress))
      return false;
    if (get(modelScope) === 'all')
      return get(availableChainsForAddress).length > 0;
    return get(modelSelectedChainIds).length > 0;
  });

  function reset(): void {
    const current = toValue(editing);
    if (current?.kind === 'chain') {
      set(modelKind, 'chain');
      set(modelChainId, current.chainId);
      set(modelAddress, undefined);
      set(modelSelectedChainIds, []);
      set(modelScope, 'all');
      return;
    }
    if (current?.kind === 'address') {
      set(modelKind, 'address');
      set(modelChainId, undefined);
      set(modelAddress, current.address);
      const available = get(addressOptions).find(o => o.address === current.address)?.chainIds ?? [];
      const isAllChains = available.length > 0
        && current.chainIds.length === available.length
        && available.every(c => current.chainIds.includes(c));
      set(modelScope, isAllChains ? 'all' : 'specific');
      set(modelSelectedChainIds, [...current.chainIds]);
      return;
    }
    set(modelKind, 'chain');
    set(modelChainId, undefined);
    set(modelAddress, undefined);
    set(modelSelectedChainIds, []);
    set(modelScope, 'all');
  }

  function buildDraft(): RuleDraft | undefined {
    if (!get(canSave))
      return undefined;
    if (get(modelKind) === 'chain') {
      const id = get(modelChainId);
      if (!id)
        return undefined;
      return { chainId: id, kind: 'chain' };
    }
    const addr = get(modelAddress);
    if (!addr)
      return undefined;
    const chainIds = get(modelScope) === 'all' ? get(availableChainsForAddress) : get(modelSelectedChainIds);
    return { address: addr, chainIds: [...chainIds], kind: 'address' };
  }

  watch(modelAddress, () => {
    if (get(modelKind) !== 'address' || get(modelScope) !== 'specific')
      return;
    const available = new Set(get(availableChainsForAddress));
    set(modelSelectedChainIds, get(modelSelectedChainIds).filter(c => available.has(c)));
  });

  reset();

  return {
    addressOptions,
    availableChainsForAddress,
    buildDraft,
    canSave,
    filterAddressOption,
    modelAddress,
    modelChainId,
    modelKind,
    modelScope,
    modelSelectedChainIds,
    reset,
  };
}
