import type { Ref } from 'vue';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';

export interface EvmIndexerSettings {
  defaultEvmIndexerOrder: Readonly<Ref<SettingValue<'defaultEvmIndexerOrder'>>>;
  evmIndexersOrder: Readonly<Ref<SettingValue<'evmIndexersOrder'>>>;
}

/**
 * Domain facade bundling the two EVM indexer-order settings that are consumed together (the global
 * default order and the per-chain overrides). Reads through `useSetting`, so no store is imported by
 * the consumers. Callers that also need `beaconRpcEndpoint` read it separately via `useSetting`.
 */
export function useEvmIndexerSettings(): EvmIndexerSettings {
  return {
    defaultEvmIndexerOrder: useSetting('defaultEvmIndexerOrder'),
    evmIndexersOrder: useSetting('evmIndexersOrder'),
  };
}
