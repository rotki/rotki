import type { ComputedRef } from 'vue';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useSharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import { toInternalTxConflictFields } from '@/modules/history/internal-tx-conflicts/internal-tx-conflict-fields';

/**
 * The pill-bar fields for the internal transaction conflicts table. Built inside a computed so the
 * labels track the locale: fields built once at setup keep the language they were created in until
 * the component remounts.
 */
export function useInternalTxConflictFields(): ComputedRef<FieldDef[]> {
  const { t } = useI18n({ useScope: 'global' });
  // Chain and date resolution is the same for every table filtering on them, so it comes from one
  // place rather than being restated here.
  const shared = useSharedFieldResolvers();
  const { evmChainsData } = useSupportedChains();

  // Only the chains an internal transaction can be on: the conflicts are evm-only.
  const chains = (): string[] => get(evmChainsData).map(chain => chain.evmChainName);

  return computed<FieldDef[]>(() => toInternalTxConflictFields(shared, t, chains));
}
