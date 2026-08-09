import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

/** What an asset field needs from its table: which wire key it writes, and how to search. */
export interface AssetFieldSpec {
  readonly key: string;
  readonly label: string;
  /** The async asset search backing the picker, debounced by the table that supplies it. */
  readonly searchAsset: (value: string) => Promise<AssetsWithId>;
  /** Whether the endpoint takes more than one asset. Most take exactly one. */
  readonly multiple?: boolean;
}

/**
 * The asset pill, shared by every table that filters on an asset.
 *
 * Always picked from the dedicated asset editor rather than typed: an identifier such as
 * `eip155:1/erc20:0x…` is not something anyone writes, so the field carries the search instead of
 * an option list. How the picked asset then reads - its icon, symbol and chain badge - is the
 * shared asset decoration, which is the whole reason this is one builder: the asset pill has
 * looked wrong in three separate ways over this feature's life and each fix should land once.
 *
 * No `deserializer`: a stored value is the identifier the request carries, and the symbol shown on
 * the pill is resolved for display only.
 */
export function toAssetField(spec: AssetFieldSpec, resolvers: SharedFieldResolvers): FieldDef {
  return decorateSharedField(
    toMatchFieldDef({
      key: spec.key,
      label: spec.label,
      multiple: spec.multiple ?? false,
      searchAsset: spec.searchAsset,
      valueType: FilterValueTypes.ASSET,
    }),
    SharedFieldKinds.ASSET,
    resolvers,
  );
}
