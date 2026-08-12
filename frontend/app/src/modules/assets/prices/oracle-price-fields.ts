import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { OraclePriceFilterKeys } from '@/modules/assets/prices/use-oracle-prices-filter';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';
import { toPeriodField } from '@/modules/core/table/filters/shared/period-field';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** What the oracle price fields need from the Vue layer to be built. */
export interface OraclePriceFieldOptions {
  /** The async asset search backing both asset pickers. */
  readonly searchAsset: (value: string) => Promise<AssetsWithId>;
  /** The oracles offered as the source field's values. */
  readonly sources: () => string[];
  /** An oracle id -> what the row it filters to calls it. */
  readonly resolveSourceLabel: (value: string) => string;
}

/**
 * The pill-bar fields for the oracle prices table: the two assets a price is quoted between, the
 * oracle it came from, and the two date bounds as one period pill.
 */
export function toOraclePriceFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: OraclePriceFieldOptions,
): FieldDef[] {
  const { resolveSourceLabel, searchAsset, sources } = options;

  return [
    toAssetField({
      key: OraclePriceFilterKeys.FROM_ASSET,
      label: t('oracle_prices.filter_field_labels.from_asset'),
      searchAsset,
    }, resolvers),
    toAssetField({
      key: OraclePriceFilterKeys.TO_ASSET,
      label: t('oracle_prices.filter_field_labels.to_asset'),
      searchAsset,
    }, resolvers),
    toMatchFieldDef({
      key: OraclePriceFilterKeys.SOURCE,
      label: t('oracle_prices.filter_field_labels.source'),
      multiple: false,
      // A raw oracle id (`cryptocompare`) is not what the table calls it, and the pill has to read
      // the same as the source chip in the row it filters to.
      resolveLabel: resolveSourceLabel,
      suggest: sources,
      validate: (value: string): boolean => sources().includes(value),
    }),
    toPeriodField(
      t('oracle_prices.filter_field_labels.period'),
      { lowerKey: OraclePriceFilterKeys.START, upperKey: OraclePriceFilterKeys.END },
      resolvers,
    ),
  ];
}
