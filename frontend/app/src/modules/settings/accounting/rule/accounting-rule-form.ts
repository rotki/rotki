import { z, type ZodType } from 'zod';
import { requiredEventSubtype, requiredEventType } from '@/modules/history/management/forms/event-field-schemas';
import {
  type AccountingRuleEntry,
  type AccountingRuleWithLinkedProperty,
  AccountingTreatment,
} from '@/modules/settings/types/accounting';

/**
 * The four identifying fields of a rule. The three linked toggles are deliberately absent: they can
 * never be invalid, and they are not part of what marks the form dirty.
 */
export interface AccountingRuleFormState {
  accountingTreatment: AccountingTreatment | null;
  counterparty: string;
  eventSubtype: string;
  eventType: string;
}

export function accountingRuleFormSchema(): ZodType<AccountingRuleFormState> {
  return z.object({
    accountingTreatment: z.enum(AccountingTreatment).nullable(),
    // A rule with no counterparty applies to every counterparty, so blank is a valid answer.
    counterparty: z.string(),
    eventSubtype: requiredEventSubtype(),
    eventType: requiredEventType(),
  });
}

/** The rule as the API stores it -> what the inputs bind to. A missing counterparty shows as blank. */
export function accountingRuleFormState(rule: AccountingRuleEntry): AccountingRuleFormState {
  return {
    accountingTreatment: rule.accountingTreatment,
    counterparty: rule.counterparty ?? '',
    eventSubtype: rule.eventSubtype,
    eventType: rule.eventType,
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
    eventSubtype: state.eventSubtype,
    eventType: state.eventType,
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
