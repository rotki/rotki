import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { toInternalTxConflictFields } from '@/modules/history/internal-tx-conflicts/internal-tx-conflict-fields';

/** The pill-bar fields for the internal transaction conflicts table. */
export function useInternalTxConflictFields(): FieldDef[] {
  const { t } = useI18n({ useScope: 'global' });
  const shared = useSharedFieldResolvers();
  const { evmChainsData } = useSupportedChains();

  /**
   * Offers every EVM chain, and nothing else, as the pill's choices.
   *
   * @remarks
   * Internal transactions exist only on EVM chains, so a conflict over one cannot be filed
   * against any other chain. The values are `evmChainName`, which is the spelling the backend
   * takes for this filter.
   */
  const chains = (): string[] => get(evmChainsData).map(chain => chain.evmChainName);

  return toInternalTxConflictFields(shared, t, chains);
}
