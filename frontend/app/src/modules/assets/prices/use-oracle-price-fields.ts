import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toOraclePriceFields } from '@/modules/assets/prices/oracle-price-fields';
import { getOracleSourceLabel, ORACLE_SOURCES } from '@/modules/assets/prices/oracle-source-labels';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/**
 * The pill-bar fields for the oracle prices table. Built inside a computed so the labels track the
 * locale: fields built once at setup keep the language they were created in until the component
 * remounts.
 */
export function useOraclePriceFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Asset and date resolution is the same for every table filtering on them, so it comes from one
  // place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const { assetSearch } = useAssetInfoRetrieval();

  // Built once, outside the computed: the search is debounced, and rebuilding it per recompute
  // would hand each keystroke a fresh timer that cancels nothing.
  const searchAsset = assetSuggestions(assetSearch);

  return computed<FieldDef[]>(() => toOraclePriceFields(shared, t, {
    resolveSourceLabel: getOracleSourceLabel,
    searchAsset,
    sources: (): string[] => ORACLE_SOURCES,
  }));
}
