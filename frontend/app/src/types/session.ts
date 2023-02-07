import { z } from 'zod';
import { type TimeFramePeriod } from '@rotki/common/lib/settings/graphs';

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
