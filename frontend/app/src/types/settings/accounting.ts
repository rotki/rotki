import type { ConflictResolutionStrategy, PaginationRequestPayload } from '@/types/common';
import { z } from 'zod/v4';
import { CollectionCommonFields } from '@/types/collection';

export enum AccountingTreatment {
  SWAP = 'swap',
}

const AccountingTreatmentEnum = z.enum(AccountingTreatment);

export const AccountingRuleWithLinkedProperty = z.object({
  linkedSetting: z.string().optional(),
  value: z.boolean(),
});

export type AccountingRuleWithLinkedProperty = z.infer<typeof AccountingRuleWithLinkedProperty>;

export const AccountingRuleIdentifier = z.object({
  counterparty: z.string().nullable(),
  eventIds: z.array(z.number()).nullish(),
  eventSubtype: z.string(),
  eventType: z.string(),
});

export type AccountingRuleIdentifier = z.infer<typeof AccountingRuleIdentifier>;

export const AccountingRule = z.object({
  ...AccountingRuleIdentifier.shape,
  accountingTreatment: AccountingTreatmentEnum.nullable(),
  countCostBasisPnl: AccountingRuleWithLinkedProperty,
  countEntireAmountSpend: AccountingRuleWithLinkedProperty,
  taxable: AccountingRuleWithLinkedProperty,
});

export type AccountingRule = z.infer<typeof AccountingRule>;

const AccountingRuleEntry = AccountingRule.extend({
  identifier: z.number(),
});

export type AccountingRuleEntry = z.infer<typeof AccountingRuleEntry>;

export const AccountingRuleEntryCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(AccountingRuleEntry),
});

export type AccountingRuleEntryCollectionResponse = z.infer<typeof AccountingRuleEntryCollectionResponse>;

export interface AccountingRuleRequestPayload extends PaginationRequestPayload<AccountingRuleEntry> {
  readonly eventTypes?: string[];
  readonly eventSubtypes?: string[];
  readonly counterparties?: (string | null)[];
  readonly customRuleHandling?: boolean;
  readonly eventIds?: number[];
  readonly identifiers?: number[];
}

export interface AccountingRuleLinkedSettingMap {
  identifier: string;
  label: string;
  state: boolean;
}

export const AccountingRuleConflict = z.object({
  localData: AccountingRule,
  localId: z.number(),
  remoteData: AccountingRule,
});

export type AccountingRuleConflict = z.infer<typeof AccountingRuleConflict>;

export const AccountingRuleConflictCollectionResponse = CollectionCommonFields.extend({
  entries: z.array(AccountingRuleConflict),
});

export interface AccountingRuleConflictRequestPayload extends PaginationRequestPayload<AccountingRuleConflict> {}

export interface AccountingRuleConflictAllResolution {
  solveAllUsing: ConflictResolutionStrategy;
}

export interface AccountingRuleConflictManualResolution {
  localId: string;
  solveUsing: ConflictResolutionStrategy;
}

export type AccountingRuleConflictResolution =
  | AccountingRuleConflictAllResolution
  | { conflicts: AccountingRuleConflictManualResolution[] };

export type AccountingRuleAction = 'add-general' | 'add-event-specific' | 'edit-general' | 'edit-event-specific';

export const AccountingRuleLinkedMappingSchema = z.record(z.string(), z.array(z.string()));

export type AccountingRuleLinkedMapping = z.infer<typeof AccountingRuleLinkedMappingSchema>;
