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
 * Assembles the pill-bar fields for the managed assets table.
 *
 * @remarks
 * The fields it sends in its filter bag, plus three param-bound pills: owned only, whitelisted
 * only, and how ignored assets are handled. Assembled here so every filter this table has is
 * declared in one place.
 */
export function useManagedAssetFields(
  assetTypes: MaybeRefOrGetter<string[]>,
  ignoredCount: MaybeRefOrGetter<number>,
): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const { allEvmChains } = useSupportedChains();

  /**
   * Lists every chain value the chain pill accepts.
   *
   * @remarks
   * The backend takes hyperliquid and solana under the same filter key as the evm chains, but
   * neither appears in `allEvmChains`, so both are appended by hand.
   */
  const chains = (): string[] => [
    ...get(allEvmChains).map(chain => chain.name),
    HYPERLIQUID_CORE_CHAIN,
    SOLANA_CHAIN,
  ];

  /**
   * Labels one ignored-asset handling value, folding the ignored count into the narrowing choice.
   *
   * @remarks
   * The count is part of what the value means rather than decoration beside it: picking "ignored
   * only" is a different decision when nothing is ignored.
   *
   * @param value - an `IgnoredAssetHandlingType`; anything else falls back to the "all" label.
   */
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
