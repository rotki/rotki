import type { LocationQuery } from 'vue-router';
import { useAddQuery } from '@/modules/core/common/use-add-query';
import { firstQueryValue } from '@/modules/core/table/route';

/** What an `?add=` link to a price table names. */
export interface PriceAddLink {
  /** The asset to price, or an empty string when the link names none. */
  fromAsset: string;
  /** When the price applies, in seconds; 0 when the link names no time. */
  timestamp: number;
}

function readPriceAddLink(query: LocationQuery): PriceAddLink {
  const timestamp = Number(firstQueryValue(query.timestamp));
  return {
    fromAsset: firstQueryValue(query.fromAsset),
    timestamp: Number.isFinite(timestamp) && timestamp > 0 ? timestamp : 0,
  };
}

/**
 * The `?add=` deep link of the price tables, read into the asset and the time it names.
 *
 * @remarks
 * A missing price in the backend problems drawer links here with both, so the add dialog opens
 * on the price that is missing.
 *
 * @param onAdd - opens the add dialog, seeded from the link
 * @returns the one call the page makes, usually from `onMounted`
 */
export function usePriceAddLink(onAdd: (link: PriceAddLink) => void): ReturnType<typeof useAddQuery> {
  return useAddQuery(query => onAdd(readPriceAddLink(query)));
}
