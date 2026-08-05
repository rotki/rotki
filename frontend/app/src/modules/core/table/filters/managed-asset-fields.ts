import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { IgnoredAssetHandlingType } from '@/modules/assets/types';
import { truncateAddress } from '@/modules/core/common/display/truncate';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { AssetFilterValueKeys, type Matcher } from '@/modules/core/table/filters/use-assets-filter';
import { toFieldDef, toParamFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * Short, noun-style pill labels. The matcher `description` is a long "filter by …" hint that reads
 * badly on a pill, so each field gets a concise label keyed by its wire key.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [AssetFilterValueKeys.ADDRESS]: t('assets.filter_field_labels.address'),
    [AssetFilterValueKeys.ASSET_FLAG]: t('assets.filter_field_labels.asset_flag'),
    [AssetFilterValueKeys.ASSET_TYPE]: t('assets.filter_field_labels.asset_type'),
    [AssetFilterValueKeys.CHAIN]: t('assets.filter_field_labels.chain'),
    [AssetFilterValueKeys.IDENTIFIER]: t('assets.filter_field_labels.identifier'),
    [AssetFilterValueKeys.NAME]: t('assets.filter_field_labels.name'),
    [AssetFilterValueKeys.SYMBOL]: t('assets.filter_field_labels.symbol'),
  };
}

// Which of this table's keys are fields other tables have too. How they render comes from the
// shared library, so a fix to the chain pill lands for every table at once.
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  // The values are evm chain *names* (`ethereum`, `polygon_pos`) rather than chain ids, which both
  // the shared name resolver and the chain icon accept.
  [AssetFilterValueKeys.CHAIN]: SharedFieldKinds.CHAIN,
  // A backend asset type is already spaced words (`evm token`), so it only needs its casing fixed.
  [AssetFilterValueKeys.ASSET_TYPE]: SharedFieldKinds.TOKEN,
  [AssetFilterValueKeys.ASSET_FLAG]: SharedFieldKinds.TOKEN,
};

/**
 * String matchers with no option list: the user types the value instead of picking it. There is no
 * list of every symbol, name, identifier or contract address to offer.
 */
const freeTextKeys = new Set<string>([
  AssetFilterValueKeys.ADDRESS,
  AssetFilterValueKeys.IDENTIFIER,
  AssetFilterValueKeys.NAME,
  AssetFilterValueKeys.SYMBOL,
]);

/**
 * The two fields the backend cannot be given at once: an asset type and a chain narrow the same
 * query in ways it does not combine. The old bar expressed this by dropping the other matcher from
 * its list while one was set; the pill bar declares it on both sides and removes the excluded field
 * from the add menu and from narrowing.
 */
const exclusions: Partial<Record<string, readonly string[]>> = {
  [AssetFilterValueKeys.ASSET_TYPE]: [AssetFilterValueKeys.CHAIN],
  [AssetFilterValueKeys.CHAIN]: [AssetFilterValueKeys.ASSET_TYPE],
};

/**
 * The pill-bar fields for the managed assets table: the matcher-backed ones, with long descriptions
 * replaced by short pill labels and the type/chain pairing declared as a mutual exclusion.
 */
export function toManagedAssetFields(matchers: Matcher[], resolvers: SharedFieldResolvers, t: Translate): FieldDef[] {
  const labels = shortLabels(t);
  return matchers.map((matcher) => {
    const field = toFieldDef(matcher);
    const key = field.key;
    return {
      ...decorateSharedField(field, sharedKinds[key], resolvers),
      ...(labels[key] ? { label: labels[key] } : {}),
      ...(freeTextKeys.has(key) ? { freeText: true } : {}),
      ...(exclusions[key] ? { excludes: exclusions[key] } : {}),
      // An address typed into the bar is shown truncated: a contract address is forty-two
      // characters and would swamp the pill. Unlike an account address it is not an identity, so it
      // is not scrambled — the table shows the same address in full beside it.
      ...(key === AssetFilterValueKeys.ADDRESS ? { resolveLabel: (value: string): string => truncateAddress(value, 4) } : {}),
    };
  });
}

/**
 * The owned-assets toggle as a param-bound boolean pill. A boolean field has no editor and no value
 * segment: adding the pill turns it on, removing it turns it off, which is the whole of its state.
 */
export function toAssetOwnedField(t: Translate): FieldDef {
  return toParamFieldDef({
    key: 'owned',
    label: t('assets.filter_field_labels.owned'),
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
    label: t('assets.filter_field_labels.whitelisted'),
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
    label: t('assets.filter_field_labels.ignored'),
    multiple: false,
    paramKey: 'ignoredAssetsHandling',
    resolveLabel,
    suggest: (): string[] => [IgnoredAssetHandlingType.NONE, IgnoredAssetHandlingType.SHOW_ONLY],
    to: 'both',
  });
}
