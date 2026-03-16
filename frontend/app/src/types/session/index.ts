import type { TimeFramePeriod } from '@rotki/common';
import type { Module } from '@/types/modules';
import { z } from 'zod/v4';

export const PeriodicClientQueryResultSchema = z.object({
  connectedNodes: z.record(z.string(), z.array(z.string())),
  coolingDownNodes: z.record(z.string(), z.array(z.string())).optional(),
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
  ASSET_MOVEMENT_MATCHING = 'assetMovementMatching',
  GNOSIS_PAY = 'gnosispay',
  MONERIUM = 'monerium',
}

export const PremiumFeatureCapability = z.object({
  enabled: z.boolean().default(false),
  minimumTier: z.string().nullable().default(null),
});

export type PremiumFeatureCapability = z.infer<typeof PremiumFeatureCapability>;

export const PremiumCapabilities = z.object({
  assetMovementMatching: PremiumFeatureCapability.optional(),
  currentTier: z.string().optional(),
  ethStakedLimit: z.number().optional(),
  ethStakingView: PremiumFeatureCapability.optional(),
  eventAnalysisView: PremiumFeatureCapability.optional(),
  gnosispay: PremiumFeatureCapability.optional(),
  graphsView: PremiumFeatureCapability.optional(),
  historyEventsLimit: z.number().optional(),
  limitOfDevices: z.number().optional(),
  maxBackupSizeMb: z.number().optional(),
  monerium: PremiumFeatureCapability.optional(),
  pnlEventsLimit: z.number().optional(),
  reportsLookupLimit: z.number().optional(),
});

export type PremiumCapabilities = z.infer<typeof PremiumCapabilities>;
