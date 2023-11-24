import { z } from 'zod';
import { CollectionCommonFields } from '@/types/collection';
import {
  type ConflictResolutionStrategy,
  type PaginationRequestPayload
} from '@/types/common';

export enum AccountingTreatment {
  SWAP = 'swap'
}

const AccountingTreatmentEnum = z.nativeEnum(AccountingTreatment);

export const AccountingRuleWithLinkedProperty = z.object({
  value: z.boolean(),
  linkedSetting: z.string().optional()
});

export type AccountingRuleWithLinkedProperty = z.infer<
  typeof AccountingRuleWithLinkedProperty
>;

export const AccountingRule = z.object({
  eventType: z.string(),
  eventSubtype: z.string(),
  counterparty: z.string().nullable(),
  taxable: AccountingRuleWithLinkedProperty,
  countCostBasisPnl: AccountingRuleWithLinkedProperty,
  countEntireAmountSpend: AccountingRuleWithLinkedProperty,
  accountingTreatment: AccountingTreatmentEnum.nullable()
});

export type AccountingRule = z.infer<typeof AccountingRule>;

const AccountingRuleEntry = AccountingRule.extend({
  identifier: z.number()
});

export type AccountingRuleEntry = z.infer<typeof AccountingRuleEntry>;

export const AccountingRuleEntryCollectionResponse =
  CollectionCommonFields.extend({
    entries: z.array(AccountingRuleEntry)
  });

export type AccountingRuleEntryCollectionResponse = z.infer<
  typeof AccountingRuleEntryCollectionResponse
>;

export interface AccountingRuleRequestPayload
  extends PaginationRequestPayload<AccountingRuleEntry> {
  readonly eventTypes?: string[];
  readonly eventSubtypes?: string[];
  readonly counterparties?: string[];
}

export interface AccountingRuleLinkedSettingMap {
  identifier: string;
  label: string;
  state: boolean;
}

export const AccountingRuleConflict = z.object({
  localId: z.number(),
  localData: AccountingRule,
  remoteData: AccountingRule
});

export type AccountingRuleConflict = z.infer<typeof AccountingRuleConflict>;

export const AccountingRuleConflictCollectionResponse =
  CollectionCommonFields.extend({
    entries: z.array(AccountingRuleConflict)
  });

export interface AccountingRuleConflictRequestPayload
  extends PaginationRequestPayload<AccountingRuleConflict> {}

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
