import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import { assert, Blockchain } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { getPublicProtocolImagePath, getPublicServiceImagePath } from '@/modules/core/common/file/file';
import { isOfEnum } from '@/modules/core/common/helpers/is-of-enum';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';

export const RpcSettingKey = {
  BEACON: 'beaconRpcEndpoint',
  BTC_MEMPOOL: 'btcMempoolApi',
  DOT: 'dotRpcEndpoint',
  KSM: 'ksmRpcEndpoint',
} as const;

export type RpcSettingKey = typeof RpcSettingKey[keyof typeof RpcSettingKey];

export interface ChainRpcSettingTab {
  chain: Blockchain;
  setting?: RpcSettingKey;
}

interface CustomRpcSettingTab {
  id: string;
  name: string;
  image: string;
  setting: RpcSettingKey;
}

export type RpcSettingTab = ChainRpcSettingTab | CustomRpcSettingTab;

interface RpcRailOption {
  key: string;
  label: string;
  tab: RpcSettingTab;
  group: 'evm' | 'other';
}

export function isChainTab(item: RpcSettingTab): item is ChainRpcSettingTab {
  return 'chain' in item;
}

export function tabKey(tab: RpcSettingTab): string {
  return isChainTab(tab) ? tab.chain : tab.id;
}

export interface UseRpcSettingsTabsReturn {
  selectedKey: DeepReadonly<Ref<string>>;
  rpcSettingTabs: ComputedRef<RpcSettingTab[]>;
  evmRailOptions: ComputedRef<RpcRailOption[]>;
  otherRailOptions: ComputedRef<RpcRailOption[]>;
  allRailOptions: ComputedRef<RpcRailOption[]>;
  firstOtherKey: ComputedRef<string | undefined>;
  activeTab: ComputedRef<RpcSettingTab | undefined>;
  canAddNode: ComputedRef<boolean>;
  selectTab: (key: string | null | undefined) => void;
}

export function useRpcSettingsTabs(): UseRpcSettingsTabsReturn {
  const route = useRoute();
  const router = useRouter();
  const { getChainName, txEvmChains } = useSupportedChains();

  /**
   * The selected tab, held as its key rather than its position.
   *
   * @remarks
   * A key is either a chain id or a custom tab id. `txEvmChains` may load after mount, so a position
   * would point at a different tab once the list grows.
   */
  const selectedKey = ref<string>(Blockchain.ETH);

  const evmChainTabs = useArrayMap(txEvmChains, (chain): RpcSettingTab => {
    assert(isOfEnum(Blockchain)(chain.id));
    return { chain: chain.id };
  });

  const otherTabs = computed<RpcSettingTab[]>(() => [
    // Solana is non-EVM but uses the same multi-node RPC manager as EVM chains.
    { chain: Blockchain.SOLANA },
    {
      id: 'btc_mempool_space',
      image: getPublicServiceImagePath('mempool.png'),
      name: 'Bitcoin Mempool',
      setting: RpcSettingKey.BTC_MEMPOOL,
    },
    { chain: Blockchain.KSM, setting: RpcSettingKey.KSM },
    { chain: Blockchain.DOT, setting: RpcSettingKey.DOT },
    {
      id: 'eth_consensus_layer',
      image: getPublicProtocolImagePath('ethereum.svg'),
      name: 'ETH Beacon Node',
      setting: RpcSettingKey.BEACON,
    },
  ]);

  const rpcSettingTabs = computed<RpcSettingTab[]>(() => [
    ...get(evmChainTabs),
    ...get(otherTabs),
  ]);

  function toRailOption(group: 'evm' | 'other') {
    return (tab: RpcSettingTab): RpcRailOption => ({
      key: tabKey(tab),
      label: isChainTab(tab) ? getChainName(tab.chain) : tab.name,
      tab,
      group,
    });
  }

  const evmRailOptions = computed<RpcRailOption[]>(() => get(evmChainTabs).map(toRailOption('evm')));
  const otherRailOptions = computed<RpcRailOption[]>(() => get(otherTabs).map(toRailOption('other')));
  const allRailOptions = computed<RpcRailOption[]>(() => [...get(evmRailOptions), ...get(otherRailOptions)]);
  const firstOtherKey = computed<string | undefined>(() => get(otherRailOptions)[0]?.key);

  const activeTab = computed<RpcSettingTab | undefined>(() => {
    const key = get(selectedKey);
    return get(rpcSettingTabs).find(tab => tabKey(tab) === key);
  });

  /**
   * Whether this tab's chain can hold more than one node.
   *
   * @remarks
   * A tab carrying a `setting` key is a single-value endpoint (BTC Mempool, KSM, DOT, Beacon) that
   * stores one url, so there is nothing for an "Add node" button to add.
   */
  const canAddNode = computed<boolean>(() => {
    const tab = get(activeTab);
    return !!tab && !tab.setting;
  });

  function selectTab(key: string | null | undefined): void {
    if (key)
      set(selectedKey, key);
  }

  watch(() => get(route).query.tab, (tab) => {
    if (typeof tab !== 'string' || !tab)
      return;
    if (get(selectedKey) !== tab)
      set(selectedKey, tab);
  }, { immediate: true });

  // State → route: keep the URL in sync when the user picks a tab.
  watch(selectedKey, (key) => {
    if (!key)
      return;
    const currentRoute = get(route);
    if (currentRoute.query.tab === key)
      return;
    startPromise(router.replace({
      query: { ...currentRoute.query, tab: key },
    }));
  });

  return {
    selectedKey: readonly(selectedKey),
    rpcSettingTabs,
    evmRailOptions,
    otherRailOptions,
    allRailOptions,
    firstOtherKey,
    activeTab,
    canAddNode,
    selectTab,
  };
}
