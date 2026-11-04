import type { MaybeRefOrGetter } from 'vue';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { NO_COLLECTION_RESOLVE, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';

interface UseFeeNotesReturn {
  appendFeeNotes: (notes: string) => string;
}

/**
 * Appends the fees of a grouped row (swap, bridge, matched movement) to its compact notes.
 *
 * @param events - the group's events; the ones with the `fee` subtype are the fees
 */
export function useFeeNotes(events: MaybeRefOrGetter<HistoryEventEntry[]>): UseFeeNotesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { getAssetField } = useAssetInfoRetrieval();

  /** Returns `notes` unchanged when the group has no fee events. */
  function appendFeeNotes(notes: string): string {
    const fees = toValue(events).filter(item => item.eventSubtype === 'fee');
    if (fees.length === 0)
      return notes;

    const feeText = fees
      .map(item => `${item.amount.toFixed()} ${getAssetField(item.asset, 'symbol', NO_COLLECTION_RESOLVE)}`)
      .join('; ');
    return t('history_events_list_swap.fee_description', { feeText, notes });
  }

  return { appendFeeNotes };
}
