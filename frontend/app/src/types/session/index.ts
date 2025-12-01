import type { TimeFramePeriod } from '@rotki/common';
import type { Module } from '@/types/modules';
import { z } from 'zod/v4';

export const PeriodicClientQueryResultSchema = z.object({
  connectedNodes: z.record(z.string(), z.array(z.string())),
  failedToConnect: z.record(z.string(), z.array(z.string())).optional(),
  lastBalanceSave: z.number(),
  lastDataUploadTs: z.number(),
});

export type PeriodicClientQueryResult = z.infer<typeof PeriodicClientQueryResultSchema>;

export const MessagesSchema = z.object({
  errors: z.array(z.string()),
  warnings: z.array(z.string()),
});

export type Messages = z.infer<typeof MessagesSchema>;

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
  timeframe: TimeFramePeriod;
  animationsEnabled: boolean;
}

export const QueriedAddressesSchema = z.record(z.string(), z.array(z.string()));

export type QueriedAddresses = z.infer<typeof QueriedAddressesSchema>;

export interface QueriedAddressPayload {
  readonly module: Module;
  readonly address: string;
}

export enum PremiumFeature {
  ETH_STAKING_VIEW = 'ethStakingView',
  EVENT_ANALYSIS_VIEW = 'eventAnalysisView',
  GRAPHS_VIEW = 'graphsView',
}

export const PremiumCapabilities = z.record(
  z.enum(PremiumFeature),
  z.boolean().default(false),
);

export type PremiumCapabilities = z.infer<typeof PremiumCapabilities>;
