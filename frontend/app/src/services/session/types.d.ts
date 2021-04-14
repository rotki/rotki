import { MODULES, PURGABLE } from '@/services/session/consts';

export type WatcherType = 'makervault_collateralization_ratio';
export type WatcherTypes = WatcherType;
export type WatcherOpTypes = 'lt' | 'le' | 'gt' | 'ge';

export interface Watcher<T extends WatcherTypes> {
  readonly identifier: string;
  readonly type: T;
  readonly args: WatcherArgs[T];
}

interface MakerVaultCollateralizationRatio {
  readonly ratio: string;
  readonly op: WatcherOpTypes;
  readonly vault_id: string;
}

interface WatcherArgs {
  readonly makervault_collateralization_ratio: MakerVaultCollateralizationRatio;
}

export type SupportedModules = typeof MODULES[number];

export type QueriedAddresses = {
  readonly [module in SupportedModules]?: string[];
};

export interface QueriedAddressPayload {
  readonly module: SupportedModules;
  readonly address: string;
}

export type Purgeable = typeof PURGABLE[number];
