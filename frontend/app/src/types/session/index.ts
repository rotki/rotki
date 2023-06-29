import { z } from 'zod';
import { type TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { type Module } from '@/types/modules';

export const PeriodicClientQueryResult = z.object({
  lastBalanceSave: z.number(),
  lastDataUploadTs: z.number(),
  connectedNodes: z.record(z.array(z.string()))
});

export type PeriodicClientQueryResult = z.infer<
  typeof PeriodicClientQueryResult
>;

export const Messages = z.object({
  warnings: z.array(z.string()),
  errors: z.array(z.string())
});

export type Messages = z.infer<typeof Messages>;

export enum PrivacyMode {
  NORMAL = 0,
  SEMI_PRIVATE = 1,
  PRIVATE = 2
}

export interface Pinned {
  name: string;
  props: Record<string, any>;
}

export interface PremiumCredentialsPayload {
  readonly username: string;
  readonly apiKey: string;
  readonly apiSecret: string;
}

export interface ChangePasswordPayload {
  readonly currentPassword: string;
  readonly newPassword: string;
}

export interface SessionSettings {
  privacyMode: PrivacyMode;
  scrambleData: boolean;
  scrambleMultiplier: number;
  timeframe: TimeFramePeriod;
  animationsEnabled: boolean;
}

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
