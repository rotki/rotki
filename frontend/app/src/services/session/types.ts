import { z } from 'zod';
import { type PURGABLE } from '@/services/session/consts';
import { type Module } from '@/types/modules';

export const WatcherType = 'makervault_collateralization_ratio';

export const WatcherOpTypes = z.enum(['lt', 'le', 'gt', 'ge']);
export type WatcherOpTypes = z.infer<typeof WatcherOpTypes>;

export const BaseWatcher = z.object({
  identifier: z.string()
});

export const MakerVaultCollateralizationRatioArgs = z.object({
  ratio: z.string(),
  op: WatcherOpTypes,
  vaultId: z.string()
});

export const MakerVaultCollateralizationRatioWatcher = BaseWatcher.extend({
  type: z.literal(WatcherType),
  args: MakerVaultCollateralizationRatioArgs
});

export type MakerVaultCollateralizationRatioWatcher = z.infer<
  typeof MakerVaultCollateralizationRatioWatcher
>;

export const Watcher = MakerVaultCollateralizationRatioWatcher;
export type Watcher = z.infer<typeof Watcher>;

export const Watchers = z.array(Watcher);
export type Watchers = z.infer<typeof Watchers>;

export type QueriedAddresses = {
  readonly [module in Module]?: string[];
};

export interface QueriedAddressPayload {
  readonly module: Module;
  readonly address: string;
}

export type Purgeable = typeof PURGABLE[number];
