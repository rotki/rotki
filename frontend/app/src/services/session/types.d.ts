export type WatcherType = 'makervault_collateralization_ratio';
export type WatcherTypes = WatcherType;
export type WatcherOpTypes = 'lt' | 'le' | 'gt' | 'ge';

export interface Watcher<T extends WatcherTypes> {
  readonly identifier: string;
  readonly type: T;
  readonly args: WatcherArgs[T];
}

export interface MakerVaultCollateralizationRatio {
  readonly ratio: string;
  readonly op: WatcherOpTypes;
  readonly vault_id: string;
}

export interface WatcherArgs {
  readonly makervault_collateralization_ratio: MakerVaultCollateralizationRatio;
}
