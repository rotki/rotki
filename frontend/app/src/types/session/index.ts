import type { TimeFramePeriod } from '@rotki/common';
import type { CamelCase } from '@/types/common';
import type { Module } from '@/types/modules';
import { z } from 'zod/v4';

export const PeriodicClientQueryResult = z.object({
  connectedNodes: z.record(z.string(), z.array(z.string())),
  failedToConnect: z.record(z.string(), z.array(z.string())).optional(),
  lastBalanceSave: z.number(),
  lastDataUploadTs: z.number(),
});

export type PeriodicClientQueryResult = z.infer<typeof PeriodicClientQueryResult>;

export const Messages = z.object({
  errors: z.array(z.string()),
  warnings: z.array(z.string()),
});

export type Messages = z.infer<typeof Messages>;

export enum PrivacyMode {
  NORMAL = 0,
  SEMI_PRIVATE = 1,
  PRIVATE = 2,
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
  timeframe: TimeFramePeriod;
  animationsEnabled: boolean;
}

export type QueriedAddresses = {
  readonly [module in CamelCase<Module>]?: string[];
};

export interface QueriedAddressPayload {
  readonly module: Module;
  readonly address: string;
}
