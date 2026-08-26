import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { AccountingRuleFilterKeys } from '@/modules/settings/accounting/rule/use-accounting-rule-filter';

type Translate = (key: string) => string;

/**
 * What the accounting rule fields need from the Vue layer to be built.
 *
 * The two event enums are named through the backend's event mappings, because the table renders the
 * same values through them: casing the raw wire token instead reads `Deposit asset` beside a row
 * saying `Deposit Asset`, and would stay English in every other locale.
 */
export interface AccountingRuleFieldOptions {
  readonly eventTypes: () => string[];
  readonly eventTypeName: (value: string) => string;
  readonly eventSubtypes: () => string[];
  readonly eventSubtypeName: (value: string) => string;
  /**
   * The same lookup as a function of the types, rather than of the current selection: what the
   * subtype field `admits` is asked for the types the bar is about to hold, not the ones it holds.
   */
  readonly subtypesFor: (eventTypes: readonly string[]) => string[];
  readonly counterparties: () => string[];
}

/**
 * The pill-bar fields for the accounting rules table: the event type, its subtype, and the
 * counterparty a rule is written for. All three are picked from what the backend knows, and all
 * three take more than one value.
 *
 * The two event fields are declared here rather than in `filters/shared/`: history is the only other
 * table filtering on them and it still builds them from matchers, so there is no second call site to
 * shape a shared builder from yet.
 */
export function toAccountingRuleFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: AccountingRuleFieldOptions,
): FieldDef[] {
  return [
    toMatchFieldDef({
      key: AccountingRuleFilterKeys.EVENT_TYPE,
      label: (): string => t('accounting_settings.rule.filter_field_labels.event_type'),
      multiple: true,
      resolveLabel: options.eventTypeName,
      suggest: options.eventTypes,
    }),
    toMatchFieldDef({
      admits: values => options.subtypesFor(values[AccountingRuleFilterKeys.EVENT_TYPE] ?? []),
      key: AccountingRuleFilterKeys.EVENT_SUBTYPE,
      label: (): string => t('accounting_settings.rule.filter_field_labels.event_subtype'),
      multiple: true,
      resolveLabel: options.eventSubtypeName,
      suggest: options.eventSubtypes,
    }),
    // The counterparty is the shared protocol kind, so it looks the same here as in the history bar.
    decorateSharedField(
      toMatchFieldDef({
        key: AccountingRuleFilterKeys.COUNTERPARTY,
        label: (): string => t('accounting_settings.rule.filter_field_labels.counterparty'),
        multiple: true,
        suggest: options.counterparties,
      }),
      SharedFieldKinds.PROTOCOL,
      resolvers,
    ),
  ];
}
