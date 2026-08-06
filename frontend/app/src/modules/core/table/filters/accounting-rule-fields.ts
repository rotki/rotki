import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { AccountingRuleFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-accounting-rule-filter';
import { toFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * Short, noun-style pill labels. The matcher `description` is a long "filter by …" hint that reads
 * badly on a pill, so each field gets a concise label keyed by its wire key.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [AccountingRuleFilterValueKeys.COUNTERPARTY]: t('accounting_settings.rule.filter_field_labels.counterparty'),
    [AccountingRuleFilterValueKeys.EVENT_SUBTYPE]: t('accounting_settings.rule.filter_field_labels.event_subtype'),
    [AccountingRuleFilterValueKeys.EVENT_TYPE]: t('accounting_settings.rule.filter_field_labels.event_type'),
  };
}

// Only the counterparty is a shared kind, so a protocol looks the same here as in the history bar.
// The type and subtype are named by the backend's own mappings instead (see below).
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  [AccountingRuleFilterValueKeys.COUNTERPARTY]: SharedFieldKinds.PROTOCOL,
};

/**
 * How the two event enums are named. The table renders the same values through the backend's event
 * mappings, so the pill has to use them too: casing the raw wire token instead reads `Deposit asset`
 * beside a row saying `Deposit Asset`, and would stay English in every other locale.
 */
export interface AccountingRuleEventNames {
  readonly eventTypeName: (value: string) => string;
  readonly eventSubtypeName: (value: string) => string;
}

/** The pill-bar fields for the accounting rules table: the same three matchers, drawn as pills. */
export function toAccountingRuleFields(
  matchers: Matcher[],
  resolvers: SharedFieldResolvers,
  t: Translate,
  names: AccountingRuleEventNames,
): FieldDef[] {
  const labels = shortLabels(t);
  const resolveLabels: Partial<Record<string, (value: string) => string>> = {
    [AccountingRuleFilterValueKeys.EVENT_SUBTYPE]: names.eventSubtypeName,
    [AccountingRuleFilterValueKeys.EVENT_TYPE]: names.eventTypeName,
  };

  return matchers.map((matcher) => {
    const field = decorateSharedField(toFieldDef(matcher), sharedKinds[String(matcher.keyValue)], resolvers);
    const resolveLabel = resolveLabels[field.key];
    return {
      ...field,
      ...(labels[field.key] ? { label: labels[field.key] } : {}),
      ...(resolveLabel ? { resolveLabel } : {}),
    };
  });
}
