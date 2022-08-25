import { PURGABLE } from '@/services/session/consts';
import { Module } from '@/types/modules';

export type WatcherType = 'makervault_collateralization_ratio';
export type WatcherTypes = WatcherType;
export type WatcherOpTypes = 'lt' | 'le' | 'gt' | 'ge';

export interface Watcher<T extends WatcherTypes> {
  readonly identifier: string;
  readonly type: T;
  readonly args: WatcherArgs[T];
}

interface MakerVaultCollateralizationRatio {
  ratio: string;
  op: WatcherOpTypes;
  vault_id: string;
}

interface WatcherArgs {
  readonly makervault_collateralization_ratio: MakerVaultCollateralizationRatio;
}

export type QueriedAddresses = {
  readonly [module in Module]?: string[];
};

export interface QueriedAddressPayload {
  readonly module: Module;
  readonly address: string;
}

export type Purgeable = typeof PURGABLE[number];
