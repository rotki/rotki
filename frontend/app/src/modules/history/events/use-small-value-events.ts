import type { BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { normalizeTimestamp } from '@/modules/assets/amount-display/types';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useSetting } from '@/modules/settings/use-setting';

/** The fields of a history event that its value at the time it happened is worked out from. */
export interface SmallValueSubject {
  asset: string;
  amount: BigNumber;
  /** Milliseconds, as history events carry it. */
  timestamp: number;
}

interface UseSmallValueEventsReturn {
  /** Whether the user asked for small value events to be de-emphasized. */
  enabled: ComputedRef<boolean>;
  /** The value, in the main currency, below which an event counts as small. */
  threshold: ComputedRef<number>;
  /**
   * Whether the event is worth less than the threshold. Reactive when called inside a computed or a
   * render, so the answer follows the price as it resolves.
   */
  isSmallValue: (subject: SmallValueSubject) => boolean;
}

/**
 * Whether an event priced at `price` and worth `value` falls below `threshold`.
 *
 * @remarks
 * Only a known price can classify an event. The price cache reports a price that is still loading or
 * that no oracle has as a non-positive number, and a row whose worth is not yet known must keep
 * showing normally rather than flash dimmed and back.
 */
export function isBelowThreshold(price: BigNumber, value: BigNumber, threshold: number): boolean {
  return price.gt(0) && value.lt(threshold);
}

/**
 * Classifies history events by their value at the time they happened, against the threshold the user
 * set for de-emphasizing small value events.
 *
 * @remarks
 * The value comes from the historic price cache a row displays it from, so classifying a row that
 * shows its value costs no extra price query. Nothing is priced while the setting is off.
 */
export function useSmallValueEvents(): UseSmallValueEventsReturn {
  const deemphasize = useSetting('deemphasizeSmallValueEvents');
  const thresholdSetting = useSetting('smallValueEventThreshold');
  const { getHistoricPrice } = useHistoricPriceCache();

  const enabled = computed<boolean>(() => get(deemphasize));
  const threshold = computed<number>(() => get(thresholdSetting));

  function isSmallValue({ amount, asset, timestamp }: SmallValueSubject): boolean {
    const seconds = normalizeTimestamp({ ms: timestamp }) ?? 0;
    if (!get(enabled) || !asset || seconds <= 0)
      return false;

    const price = getHistoricPrice(asset, seconds);
    return isBelowThreshold(price, amount.abs().multipliedBy(price), get(threshold));
  }

  return {
    enabled,
    isSmallValue,
    threshold,
  };
}
