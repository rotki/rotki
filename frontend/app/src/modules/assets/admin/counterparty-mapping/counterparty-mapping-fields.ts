import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { CounterpartyMappingFilterKeys } from '@/modules/assets/admin/counterparty-mapping/use-counterparty-mapping-filter';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * The pill-bar fields for the counterparty mapping table: the protocol a mapping is for, and the
 * symbol that protocol calls the asset. The counterparty is the shared protocol kind, so it looks
 * the same here as in the history and accounting-rule bars.
 *
 * Both were `extraParams` before. Neither needed to be: the backend takes them as ordinary filters
 * (`CounterpartyAssetMappingsPostSchema`), so they ride the filter bag.
 */
export function toCounterpartyMappingFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  counterparties: () => string[],
): FieldDef[] {
  return [
    decorateSharedField(
      toMatchFieldDef({
        key: CounterpartyMappingFilterKeys.COUNTERPARTY,
        // The pill says what the column says.
        label: (): string => t('common.counterparty'),
        multiple: false,
        suggest: counterparties,
        validate: (value: string): boolean => counterparties().includes(value),
      }),
      SharedFieldKinds.PROTOCOL,
      resolvers,
    ),
    toNameField(
      CounterpartyMappingFilterKeys.COUNTERPARTY_SYMBOL,
      (): string => t('asset_management.cex_mapping.asset_symbol'),
    ),
  ];
}
