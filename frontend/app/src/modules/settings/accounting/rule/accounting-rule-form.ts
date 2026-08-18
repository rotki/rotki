import { z, type ZodType } from 'zod';
import { requiredEventSubtype, requiredEventType } from '@/modules/history/management/forms/event-field-schemas';
import {
  type AccountingRuleEntry,
  AccountingRuleWithLinkedProperty,
  AccountingTreatment,
} from '@/modules/settings/types/accounting';

/**
 * Everything the rule form's inputs bind to.
 *
 * The three linked toggles carry no rule of their own and must not mark the form dirty, which is
 * what `TRANSIENT_RULE_KEYS` below says. They are still part of the state: keeping them out of it
 * only moved them into a writable computed each.
 */
export interface AccountingRuleFormState {
  accountingTreatment: AccountingTreatment | null;
  counterparty: string;
  countCostBasisPnl: AccountingRuleWithLinkedProperty;
  countEntireAmountSpend: AccountingRuleWithLinkedProperty;
  eventSubtype: string;
  eventType: string;
  taxable: AccountingRuleWithLinkedProperty;
}

/**
 * The toggles, as keys the dirty comparison skips.
 *
 * They are answered by a linked setting as often as by the user, so treating a change to one as an
 * unsaved edit would have the dialog prompt on close over something the user never touched.
 */
export const TRANSIENT_RULE_KEYS = ['countCostBasisPnl', 'countEntireAmountSpend', 'taxable'] as const;

export function accountingRuleFormSchema(): ZodType<AccountingRuleFormState> {
  return z.object({
    accountingTreatment: z.enum(AccountingTreatment).nullable(),
    // A rule with no counterparty applies to every counterparty, so blank is a valid answer.
    counterparty: z.string(),
    // The three toggles carry no rule; they are named so the state parses as a whole.
    countCostBasisPnl: AccountingRuleWithLinkedProperty,
    countEntireAmountSpend: AccountingRuleWithLinkedProperty,
    eventSubtype: requiredEventSubtype(),
    eventType: requiredEventType(),
    taxable: AccountingRuleWithLinkedProperty,
  });
}

/** The rule as the API stores it -> what the inputs bind to. A missing counterparty shows as blank. */
export function accountingRuleFormState(rule: AccountingRuleEntry): AccountingRuleFormState {
  return {
    accountingTreatment: rule.accountingTreatment,
    counterparty: rule.counterparty ?? '',
    countCostBasisPnl: rule.countCostBasisPnl,
    countEntireAmountSpend: rule.countEntireAmountSpend,
    eventSubtype: rule.eventSubtype,
    eventType: rule.eventType,
    taxable: rule.taxable,
  };
}

/**
 * The inverse. The counterparty goes back verbatim, so a field the user cleared is stored as `''`
 * rather than `null` — what the vuelidate version did, since it only ever wrote what the input
 * emitted. Only a rule that arrived with no counterparty at all keeps its `null`, because this is
 * called on change and never on seed.
 */
export function applyAccountingRuleFormState(
  rule: AccountingRuleEntry,
  state: AccountingRuleFormState,
): AccountingRuleEntry {
  return {
    ...rule,
    accountingTreatment: state.accountingTreatment,
    counterparty: state.counterparty,
    countCostBasisPnl: state.countCostBasisPnl,
    countEntireAmountSpend: state.countEntireAmountSpend,
    eventSubtype: state.eventSubtype,
    eventType: state.eventType,
    taxable: state.taxable,
  };
}

/**
 * A linked property as its control needs it: the link is a flag of its own, and the setting it
 * names is always a string.
 *
 * The payload records "not linked" by leaving `linkedSetting` out, which the checkbox cannot bind
 * to and the select below it cannot open on. Naming both here is what saves the component a
 * writable computed per control.
 */
export interface LinkedPropertyState {
  linked: boolean;
  linkedSetting: string;
  value: boolean;
}

export function toLinkedPropertyState(property: AccountingRuleWithLinkedProperty): LinkedPropertyState {
  return {
    linked: Boolean(property.linkedSetting),
    linkedSetting: property.linkedSetting ?? '',
    value: property.value,
  };
}

/**
 * ⭐ A link the user asked for but which names nothing yet reads back as no link at all, which is
 * how an empty option list leaves the checkbox off. That is the behaviour the pair of writable
 * computeds this replaced already had.
 */
export function toLinkedProperty(state: LinkedPropertyState): AccountingRuleWithLinkedProperty {
  return {
    value: state.value,
    ...(state.linked && state.linkedSetting ? { linkedSetting: state.linkedSetting } : {}),
  };
}
