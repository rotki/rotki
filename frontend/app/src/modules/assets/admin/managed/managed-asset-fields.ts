import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { AssetFilterKeys } from '@/modules/assets/admin/managed/use-assets-filter';
import { AssetFlag, IgnoredAssetHandlingType } from '@/modules/assets/types';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { toNameField } from '@/modules/core/table/filters/shared/name-field';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toMatchFieldDef, toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

const assetFlags: string[] = Object.values(AssetFlag);

/**
 * The two fields the backend cannot be given at once: an asset type and a chain narrow the same
 * query in ways it does not combine. The old bar expressed this by dropping the other matcher from
 * its list while one was set; the pill bar declares it on both sides and removes the excluded field
 * from the add menu and from narrowing.
 */
const EXCLUDES_CHAIN: readonly string[] = [AssetFilterKeys.CHAIN];
const EXCLUDES_ASSET_TYPE: readonly string[] = [AssetFilterKeys.ASSET_TYPE];

/** What the managed asset fields need from the Vue layer to be built. */
export interface ManagedAssetFieldOptions {
  /** The asset types the backend knows (`evm token`, `solana token`). */
  readonly assetTypes: () => string[];
  /** The chains an asset can be on, by evm chain name, plus the two non-evm ones. */
  readonly chains: () => string[];
}

/**
 * The pill-bar fields the managed assets table sends in its filter bag.
 *
 * Four of them are typed rather than picked — there is no list of every symbol, name, identifier or
 * contract address to offer — and the type/chain pairing is declared as a mutual exclusion.
 *
 * The chain field is declared here rather than in `filters/shared/`: the other filter-bag chain
 * field (internal tx conflicts) offers a different list and validates against it, so the two share
 * only the decoration, which `decorateSharedField` already carries.
 */
export function toManagedAssetFields(
  resolvers: SharedFieldResolvers,
  t: Translate,
  options: ManagedAssetFieldOptions,
): FieldDef[] {
  return [
    // The backend takes identifiers as a list (`DelimitedOrNormalList` -> `IN (...)`), and the URL
    // has always carried several, so the field offers several rather than only the first.
    toMatchFieldDef({
      freeText: true,
      hint: (): string => t('assets.filter.identifier_hint'),
      key: AssetFilterKeys.IDENTIFIER,
      label: (): string => t('assets.filter_field_labels.identifier'),
      multiple: true,
    }),
    // A backend asset type is already spaced words (`evm token`), so it only needs its casing fixed.
    decorateSharedField(
      toMatchFieldDef({
        excludes: EXCLUDES_CHAIN,
        key: AssetFilterKeys.ASSET_TYPE,
        label: (): string => t('assets.filter_field_labels.asset_type'),
        multiple: false,
        suggest: options.assetTypes,
      }),
      SharedFieldKinds.TOKEN,
      resolvers,
    ),
    decorateSharedField(
      toMatchFieldDef({
        hint: (): string => t('assets.filter.asset_flag_hint'),
        key: AssetFilterKeys.ASSET_FLAG,
        label: (): string => t('assets.filter_field_labels.asset_flag'),
        multiple: false,
        suggest: (): string[] => assetFlags,
        validate: (flag: string): boolean => assetFlags.includes(flag),
      }),
      SharedFieldKinds.TOKEN,
      resolvers,
    ),
    toMatchFieldDef({
      freeText: true,
      hint: (): string => t('assets.filter.symbol_hint'),
      key: AssetFilterKeys.SYMBOL,
      label: (): string => t('assets.filter_field_labels.symbol'),
      multiple: false,
    }),
    {
      ...toNameField(AssetFilterKeys.NAME, (): string => t('assets.filter_field_labels.name')),
      hint: (): string => t('assets.filter.name_hint'),
    },
    // The values are evm chain *names* (`ethereum`, `polygon_pos`) rather than chain ids, which both
    // the shared name resolver and the chain icon accept.
    decorateSharedField(
      toMatchFieldDef({
        excludes: EXCLUDES_ASSET_TYPE,
        key: AssetFilterKeys.CHAIN,
        label: (): string => t('assets.filter_field_labels.chain'),
        multiple: false,
        suggest: options.chains,
      }),
      SharedFieldKinds.CHAIN,
      resolvers,
    ),
    toMatchFieldDef({
      freeText: true,
      hint: (): string => t('assets.filter.address_hint'),
      key: AssetFilterKeys.ADDRESS,
      label: (): string => t('assets.filter_field_labels.address'),
      multiple: false,
      // An address typed into the bar is shown truncated: a contract address is forty-two
      // characters and would swamp the pill. Unlike an account address it is not an identity, so it
      // is not scrambled — the table shows the same address in full beside it.
      resolveLabel: (value: string): string => truncateAddress(value, 4),
    }),
  ];
}

/**
 * The owned-assets toggle as a param-bound boolean pill. A boolean field has no editor and no value
 * segment: adding the pill turns it on, removing it turns it off, which is the whole of its state.
 */
export function toAssetOwnedField(t: Translate): FieldDef {
  return toParamFieldDef({
    key: 'owned',
    label: (): string => t('assets.filter_field_labels.owned'),
    multiple: false,
    paramKey: 'showUserOwnedAssetsOnly',
    to: 'both',
    valueType: FilterValueTypes.BOOLEAN,
  });
}

/** The whitelisted-assets toggle as a param-bound boolean pill, like {@link toAssetOwnedField}. */
export function toAssetWhitelistedField(t: Translate): FieldDef {
  return toParamFieldDef({
    key: 'whitelisted',
    label: (): string => t('assets.filter_field_labels.whitelisted'),
    multiple: false,
    paramKey: 'showWhitelistedAssetsOnly',
    to: 'both',
    valueType: FilterValueTypes.BOOLEAN,
  });
}

/**
 * The ignored-assets handling as a param-bound, single-value pill.
 *
 * The backend takes three values, but one of them — `exclude`, hiding ignored assets — is the
 * table's default, and a pill that says what would happen anyway is a control the user has to read
 * and dismiss for nothing. So only the two departures from it are offered, and removing the pill is
 * how the default is returned to. The wire form is unchanged: the param source still sends
 * `exclude` when no pill is present.
 */
export function toAssetIgnoredField(t: Translate, resolveLabel: (value: string) => string): FieldDef {
  return toParamFieldDef({
    key: 'ignored',
    label: (): string => t('assets.filter_field_labels.ignored'),
    multiple: false,
    paramKey: 'ignoredAssetsHandling',
    resolveLabel,
    suggest: (): string[] => [IgnoredAssetHandlingType.NONE, IgnoredAssetHandlingType.SHOW_ONLY],
    to: 'both',
  });
}
