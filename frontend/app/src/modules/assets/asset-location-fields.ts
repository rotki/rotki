import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { type AccountFieldOptions, toAccountField } from '@/modules/core/table/filters/shared/account-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { type TagFieldOption, toTagsField } from '@/modules/core/table/filters/shared/tag-field';
import { toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** What the asset location fields need from the Vue layer to be built. */
export interface AssetLocationFieldOptions {
  /** The accounts this asset is actually held in, and how each reads. */
  readonly accounts: AccountFieldOptions;
  /** The locations this asset is actually held at, by their raw id (`kraken`, `polygon_pos`). */
  readonly locations: () => string[];
  /** The tags the user has defined, with the colours each is recognised by. */
  readonly tags: () => TagFieldOption[];
}

/**
 * The pill-bar fields for the per-asset locations table: where the asset is held, which account
 * holds it, and the tags on that account. All three used to be a selector of their own above the
 * table.
 *
 * Every field is param-bound, because this table has no filter bag: it filters the breakdown it
 * already has in memory rather than asking the backend. `to` is what a server-bound table would
 * declare; here only the bar's own params model reads them.
 *
 * The location is the raw id, not a display name: it is what the row carries, so the filter is a
 * comparison rather than a guess at how two different formatters spell the same chain.
 */
export function toAssetLocationFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: AssetLocationFieldOptions,
): FieldDef[] {
  return [
    decorateSharedField(
      toParamFieldDef({
        key: 'location',
        label: t('common.location'),
        // A balance is held at one location, so narrowing to two would only ever widen back to the
        // unfiltered table.
        multiple: false,
        paramKey: 'location',
        suggest: options.locations,
        to: 'both',
      }),
      SharedFieldKinds.LOCATION,
      resolvers,
    ),
    toAccountField(
      { label: t('common.account'), paramKey: 'addresses', to: 'both' },
      options.accounts,
    ),
    toTagsField(t, options.tags),
  ];
}
