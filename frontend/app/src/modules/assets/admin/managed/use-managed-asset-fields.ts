import type { MaybeRefOrGetter } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import {
  toAssetIgnoredField,
  toAssetOwnedField,
  toAssetWhitelistedField,
  toManagedAssetFields,
} from '@/modules/assets/admin/managed/managed-asset-fields';
import { HYPERLIQUID_CORE_CHAIN, IgnoredAssetHandlingType, SOLANA_CHAIN } from '@/modules/assets/types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * Assembles the pill-bar fields for the managed assets table: the ones it sends in its filter bag
 * plus the three filters that used to live in the status dropdown beside the bar — owned only,
 * whitelisted only, and how ignored assets are handled — each now a param-bound pill, so every
 * filter this table has is in one place.
 */
export function useManagedAssetFields(
  assetTypes: MaybeRefOrGetter<string[]>,
  ignoredCount: MaybeRefOrGetter<number>,
): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  // Chain and asset-type resolution is the same for every table filtering on them, so it comes
  // from one place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const { allEvmChains } = useSupportedChains();

  // The two non-evm chains an asset can be on are not in the evm chain list, but the backend takes
  // them under the same key.
  const chains = (): string[] => [
    ...get(allEvmChains).map(chain => chain.name),
    HYPERLIQUID_CORE_CHAIN,
    SOLANA_CHAIN,
  ];

  // How many assets are ignored is part of what the value says, the way it was part of the radio
  // label it replaces: picking "only ignored" is a different decision when the count is zero.
  const resolveIgnoredLabel = (value: string): string => value === IgnoredAssetHandlingType.SHOW_ONLY
    ? t('assets.filter_field_labels.ignored_only', { count: toValue(ignoredCount) })
    : t('assets.filter_field_labels.ignored_all');

  return [
    ...toManagedAssetFields(shared, t, {
      assetTypes: (): string[] => toValue(assetTypes),
      chains,
    }),
    toAssetOwnedField(t),
    toAssetWhitelistedField(t),
    toAssetIgnoredField(t, resolveIgnoredLabel),
  ];
}
