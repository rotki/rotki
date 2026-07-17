import type { TimeFramePeriod } from '@rotki/common';
import type { Module } from '@/modules/core/common/modules';
import type { Report } from '@/modules/reports/report-types';
import { z } from 'zod';

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

export const PinnedNames = {
  BALANCE_DIVERGENCE: 'balance-divergence-pinned',
  DATA_ISSUES: 'data-issues-pinned',
  INTERNAL_TX_CONFLICTS: 'internal-tx-conflicts-pinned',
  MATCH_ASSET_MOVEMENTS: 'match-asset-movements-pinned',
  REPORT_ACTIONABLE_CARD: 'report-actionable-card',
} as const;

export type PinnedName = typeof PinnedNames[keyof typeof PinnedNames];

/**
 * Typed props each pinnable panel accepts. This is the checkable boundary: pinning
 * a panel with a payload that does not match its entry fails to compile. Keep each
 * entry in sync with the corresponding `*Pinned.vue` host's `defineProps`.
 */
export interface PinnedPanelProps {
  [PinnedNames.BALANCE_DIVERGENCE]: Record<never, never>;
  [PinnedNames.DATA_ISSUES]: Record<never, never>;
  [PinnedNames.INTERNAL_TX_CONFLICTS]: {
    highlightedGroupIdentifier?: string;
    highlightedTxHash?: string;
  };
  [PinnedNames.MATCH_ASSET_MOVEMENTS]: {
    highlightedGroupIdentifier?: string;
    highlightedPotentialMatchIdentifier?: number;
    potentialMatchGroupIdentifier?: string;
  };
  [PinnedNames.REPORT_ACTIONABLE_CARD]: {
    report: Report;
    isPinned?: boolean;
  };
}

/**
 * Discriminated union over `name` so `props` is narrowed to the matching panel's
 * payload. Replaces the old untyped `props: Record<string, any>` boundary.
 */
export type Pinned = {
  [K in PinnedName]: { name: K; props: PinnedPanelProps[K] };
}[PinnedName];

/**
 * Builds a `Pinned` entry from a name and its typed props. Callers stay fully
 * checked via the generic `props` param; the single unavoidable assertion lives
 * here because TS cannot prove the generic `{ name: K; props: PinnedPanelProps[K] }`
 * collapses to one arm of the distributive `Pinned` union. This is the one place
 * the pinned payload is asserted.
 */
export function toPinned<K extends PinnedName>(name: K, props: PinnedPanelProps[K]): Pinned {
  // eslint-disable-next-line @typescript-eslint/consistent-type-assertions
  return { name, props } as Pinned;
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
  CLOUD_BACKUP = 'cloudBackup',
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
