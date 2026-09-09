import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { BlockchainRpcNode } from '@/modules/settings/types/rpc';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import {
  buildRpcProviderPlan,
  type RpcProviderCandidate,
} from '@/modules/settings/general/rpc/providers/rpc-provider-plan';
import {
  detectRpcProvider,
  getRpcProvider,
  type RpcProvider,
  type RpcProviderMatch,
} from '@/modules/settings/general/rpc/providers/rpc-providers';
import { useRpcNodesByChain } from '@/modules/settings/general/rpc/providers/use-rpc-nodes-by-chain';

interface UseRpcNodeFanOutReturn {
  /** One entry per other chain the provider serves, including those that already hold the key. */
  candidates: ComputedRef<RpcProviderCandidate[]>;
  /** The key read off the endpoint, so a backend message quoting it can be masked. */
  credential: ComputedRef<string>;
  /** The chains the user has left ticked, which is what a run walks. */
  chosen: ComputedRef<RpcProviderCandidate[]>;
  /** What the user has to do on the provider's side, empty for a provider that needs nothing. */
  enablementNote: ComputedRef<string>;
  /** Whether the user has asked for the other chains. Writable, since a checkbox binds it. */
  modelEnabled: Ref<boolean>;
  /** Whether the chains' existing nodes are still being read. */
  preparing: Readonly<Ref<boolean>>;
  provider: ComputedRef<RpcProvider | undefined>;
  reset: () => void;
  /** The chains ticked, which the picker binds against. */
  selected: Readonly<Ref<readonly string[]>>;
  toggle: (chain: string, checked: boolean) => void;
  /** The chains whose node list could not be read, so nothing is planned for them. */
  unreadableNames: ComputedRef<string>;
  /** The chains rotki supports that this provider does not serve. */
  unsupportedNames: ComputedRef<string>;
}

/**
 * Works out what one provider key can cover beyond the chain being added.
 *
 * @remarks
 * The chain the form is on is deliberately not a candidate: that node is added by the form, with
 * the weight and flags the user set on it, and this covers only the chains they are not looking at.
 *
 * @param endpoint - the endpoint typed into the node form, which is what names the provider
 * @param nodeName - the name typed into the node form, used for the other chains too
 * @param currentChain - the chain the form is adding to, which the form itself covers
 * @param chains - every chain that holds a node list
 * @returns the plan, the selection, and the flag a checkbox binds to
 */
export function useRpcNodeFanOut(
  endpoint: MaybeRefOrGetter<string>,
  nodeName: MaybeRefOrGetter<string>,
  currentChain: MaybeRefOrGetter<string>,
  chains: MaybeRefOrGetter<string[]>,
): UseRpcNodeFanOutReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getChainName } = useSupportedChains();
  const { readNodes } = useRpcNodesByChain();

  const modelEnabled = shallowRef<boolean>(false);
  const preparing = shallowRef<boolean>(false);
  const selected = ref<string[]>([]);
  const existingNodes = ref<Record<string, BlockchainRpcNode[]>>({});
  const readableChains = ref<string[]>([]);
  const unreadable = ref<string[]>([]);

  const match = computed<RpcProviderMatch | undefined>(() => detectRpcProvider(toValue(endpoint)));

  const provider = computed<RpcProvider | undefined>(() => {
    const providerId = get(match)?.providerId;
    return providerId ? getRpcProvider(providerId) : undefined;
  });

  const otherChains = computed<string[]>(() => toValue(chains).filter(chain => chain !== toValue(currentChain)));

  /**
   * Recomputed rather than stored, so renaming the node re-derives every candidate's name, and the
   * per-chain uniquing that goes with it, without reading the chains again.
   */
  const plan = computed(() => {
    const detected = get(match);
    return detected
      ? buildRpcProviderPlan(detected, get(readableChains), get(existingNodes), toValue(nodeName))
      : undefined;
  });

  const candidates = computed<RpcProviderCandidate[]>(() => get(plan)?.candidates ?? []);
  const selectable = computed<RpcProviderCandidate[]>(() => get(candidates).filter(candidate => !candidate.existing));

  const chosen = computed<RpcProviderCandidate[]>(() => {
    const picked = get(selected);
    return get(selectable).filter(candidate => picked.includes(candidate.chain));
  });

  const unsupportedNames = computed<string>(() => (get(plan)?.unsupported ?? []).map(getChainName).join(', '));
  const unreadableNames = computed<string>(() => get(unreadable).map(getChainName).join(', '));

  const enablementNote = computed<string>(() => {
    const current = get(provider);
    if (!current)
      return '';

    if (current.enablement === 'per-network')
      return t('rpc_provider_setup.enablement.per_network', { provider: current.name });

    return current.enablement === 'multichain-endpoint'
      ? t('rpc_provider_setup.enablement.multichain_endpoint', { provider: current.name })
      : '';
  });

  function toggle(chain: string, checked: boolean): void {
    const picked = get(selected).filter(item => item !== chain);
    set(selected, checked ? [...picked, chain] : picked);
  }

  function reset(): void {
    set(modelEnabled, false);
    set(selected, []);
    set(existingNodes, {});
    set(readableChains, []);
    set(unreadable, []);
  }

  /**
   * Reads what the other chains already hold, so the plan can tell which are covered.
   *
   * @remarks
   * Run as soon as a provider is recognised rather than when the offer is taken up: the count
   * belongs in the offer itself, and a read started on the tick puts a spinner between the user and
   * the thing they just asked for.
   */
  async function prepare(): Promise<void> {
    set(preparing, true);
    try {
      const existing = await readNodes(get(otherChains));
      set(existingNodes, existing.nodes);
      set(readableChains, get(otherChains).filter(chain => !existing.unreadable.includes(chain)));
      set(unreadable, existing.unreadable);
      set(selected, get(candidates).filter(candidate => !candidate.existing).map(candidate => candidate.chain));
    }
    finally {
      set(preparing, false);
    }
  }

  /**
   * Reads the other chains once per provider, not once per keystroke.
   *
   * @remarks
   * Only the provider decides which chains are candidates and which already hold one of its nodes;
   * the key only decides the endpoint each candidate is given, which is built from the plan.
   */
  watch(() => get(match)?.providerId, async (providerId) => {
    set(modelEnabled, false);
    if (!providerId) {
      reset();
      return;
    }

    await prepare();
  }, { immediate: true });

  return {
    candidates,
    chosen,
    credential: computed<string>(() => get(match)?.credentials.key ?? ''),
    enablementNote,
    modelEnabled,
    preparing: readonly(preparing),
    provider,
    reset,
    selected: readonly(selected),
    toggle,
    unreadableNames,
    unsupportedNames,
  };
}
