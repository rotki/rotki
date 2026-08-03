import type { ActionStatus } from '@/modules/core/common/action';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useEventPriceUpdate } from '@/modules/history/events/prices/use-event-price-update';

/**
 * A historic price the user has edited but not yet persisted.
 *
 * The price field lives inside `HistoryEventAssetPriceForm`, but writing it is part of *saving the
 * event*, not of rendering an input. Rather than reaching back down into the component at save time
 * through a chain of template refs, the component reports the pending write upwards and the form
 * collects the intents and runs them in one place.
 */
export interface PriceIntent {
  fromAsset: string;
  toAsset: string;
  price: string;
  timestampMs: number;
}

/** Anything that can carry a pending price write, i.e. a swap sub-event row. */
export interface PriceIntentCarrier {
  priceIntent?: PriceIntent;
}

/** The pending price writes across any number of sub-event groups, in render order. */
export function collectPriceIntents(...groups: readonly PriceIntentCarrier[][]): PriceIntent[] {
  const intents: PriceIntent[] = [];
  for (const group of groups) {
    for (const carrier of group) {
      if (carrier.priceIntent)
        intents.push(carrier.priceIntent);
    }
  }
  return intents;
}

interface UsePriceIntentsReturn {
  /** Persists the intents in order, stopping at the first failure so the event is not saved either. */
  runPriceIntents: (intents: PriceIntent[]) => Promise<ActionStatus>;
}

export function usePriceIntents(): UsePriceIntentsReturn {
  const { updatePrice } = useEventPriceUpdate();

  async function runPriceIntents(intents: PriceIntent[]): Promise<ActionStatus> {
    for (const intent of intents) {
      try {
        await updatePrice({ ...intent, mode: 'manual' });
      }
      catch (error: unknown) {
        return { message: getErrorMessage(error), success: false };
      }
    }
    return { success: true };
  }

  return { runPriceIntents };
}
