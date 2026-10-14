import type { AccountingRuleConflict } from '@/modules/settings/types/accounting';

/** The rule properties a conflict can disagree on, in the order their columns show. */
export const CONFLICT_PROPERTIES = ['taxable', 'countEntireAmountSpend', 'countCostBasisPnl', 'accountingTreatment'] as const;

export type ConflictProperty = typeof CONFLICT_PROPERTIES[number];

/**
 * Whether the local and remote versions of a conflict disagree on one property.
 *
 * @remarks
 * A switch property counts as different when either its own value or the setting it follows differs:
 * two rules that both read "taxable" can still behave apart once one of them tracks a setting.
 *
 * @param conflict - the local and remote versions of one rule
 * @param property - the property to compare
 * @returns true when the two versions would account for the event differently on that property
 */
export function propertyDiffers(conflict: AccountingRuleConflict, property: ConflictProperty): boolean {
  const { localData, remoteData } = conflict;
  if (property === 'accountingTreatment')
    return localData.accountingTreatment !== remoteData.accountingTreatment;

  const local = localData[property];
  const remote = remoteData[property];
  return local.value !== remote.value || local.linkedSetting !== remote.linkedSetting;
}
