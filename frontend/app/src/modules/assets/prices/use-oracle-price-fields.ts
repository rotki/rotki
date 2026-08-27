import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toOraclePriceFields } from '@/modules/assets/prices/oracle-price-fields';
import { getOracleSourceLabel, ORACLE_SOURCES } from '@/modules/assets/prices/oracle-source-labels';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { assetSuggestions } from '@/modules/core/common/display/assets';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';

/** The pill-bar fields for the oracle prices table. */
export function useOraclePriceFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const { assetSearch } = useAssetInfoRetrieval();

  const searchAsset = assetSuggestions(assetSearch);

  return toOraclePriceFields(shared, t, {
    resolveSourceLabel: getOracleSourceLabel,
    searchAsset,
    sources: (): string[] => ORACLE_SOURCES,
  });
}
