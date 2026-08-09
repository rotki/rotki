import type { AssetsWithId } from '@/modules/assets/types';
import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { ManualBalanceFilterKeys } from '@/modules/accounts/manual-balances/use-manual-balances-filter';
import { toAssetField } from '@/modules/core/table/filters/shared/asset-field';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { type TagFieldOption, toTagsField } from '@/modules/core/table/filters/shared/tag-field';
import { toMatchFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/** What the manual balance fields need from the Vue layer to be built. */
export interface ManualBalanceFieldOptions {
  /** The locations the user actually holds a manual balance in. */
  readonly locations: () => string[];
  /** The async asset search, already scoped to the picked location. */
  readonly searchAsset: (value: string) => Promise<AssetsWithId>;
  /** The tags the user has defined, with the colours each is recognised by. */
  readonly tags: () => TagFieldOption[];
}

/**
 * The pill-bar fields for the manual balances table: the location a balance is held in, the label
 * the user gave it, its asset, and the tags that used to sit in a selector of their own beside the
 * bar. Tags are param-bound (`tags`, to request and url), which is what lets the bar absorb them.
 */
export function toManualBalanceFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: ManualBalanceFieldOptions,
): FieldDef[] {
  const { locations, searchAsset, tags } = options;

  return [
    decorateSharedField(
      toMatchFieldDef({
        key: ManualBalanceFilterKeys.LOCATION,
        label: t('common.location'),
        multiple: false,
        suggest: locations,
        // Checked against the same list it offers, so a location the user has no balance in is
        // never applied.
        validate: (value: string): boolean => locations().includes(value),
      }),
      SharedFieldKinds.LOCATION,
      resolvers,
    ),
    toNameField(ManualBalanceFilterKeys.LABEL, t('common.label')),
    toAssetField({
      key: ManualBalanceFilterKeys.ASSET,
      label: t('common.asset'),
      searchAsset,
    }, resolvers),
    toTagsField(t, tags),
  ];
}
