import { z } from 'zod';
import { type TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { type Module } from '@/types/modules';

export const PeriodicClientQueryResult = z.object({
  lastBalanceSave: z.number(),
  lastDataUploadTs: z.number(),
  connectedEthNodes: z.array(z.string()),
  connectedOptimismNodes: z.array(z.string())
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
  timeframe: TimeFramePeriod;
  animationsEnabled: boolean;
}

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
