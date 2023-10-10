import { z } from 'zod';
import { CollectionCommonFields } from '@/types/collection';
import { type PaginationRequestPayload } from '@/types/common';

export enum AccountingMethod {
  SPEND = 'spend',
  ACQUISITION = 'acquisition'
}

const AccountingMethodEnum = z.nativeEnum(AccountingMethod);

export enum AccountingTreatment {
  SWAP = 'swap',
  SWAP_WITH_FEE = 'swap with fee'
}

const AccountingTreatmentEnum = z.nativeEnum(AccountingTreatment);

const DeleteAccountingRulePayload = z.object({
  eventType: z.string(),
  eventSubtype: z.string(),
  counterparty: z.string().nullable()
});

export type DeleteAccountingRulePayload = z.infer<
  typeof DeleteAccountingRulePayload
>;

export const AccountingRule = DeleteAccountingRulePayload.extend({
  taxable: z.boolean(),
  countCostBasisPnl: z.boolean(),
  countEntireAmountSpend: z.boolean(),
  method: AccountingMethodEnum,
  accountingTreatment: AccountingTreatmentEnum
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
