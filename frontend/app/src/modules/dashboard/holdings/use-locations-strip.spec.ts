import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { ref } from 'vue';
import { type SourceContribution, SourceKind } from '@/modules/dashboard/holdings/core/holdings-types';
import { mergeLocations } from '@/modules/dashboard/holdings/core/location-holdings';
import { useLocationsStrip } from '@/modules/dashboard/holdings/use-locations-strip';

/** Two columns of 210px tiles with an 8px gap, so two rows hold four tiles. */
const TWO_COLUMNS = 428;

function exchange(location: string, value: number): SourceContribution {
  return { kind: SourceKind.EXCHANGE, loading: false, location, value: bigNumberify(value) };
}

const holdings = mergeLocations([
  exchange('kraken', 60),
  exchange('binance', 50),
  exchange('bitstamp', 40),
  exchange('gemini', 30),
  exchange('kucoin', 20),
  exchange('okx', 10),
  { kind: SourceKind.MANUAL, loading: false, location: 'kraken', value: bigNumberify(5) },
], { locationOfChain: () => undefined });

function keys(items: readonly { place: { key: string } }[]): string[] {
  return items.map(item => item.place.key);
}

describe('useLocationsStrip', () => {
  it('should cap the tiles at two rows and total what is hidden', () => {
    const strip = useLocationsStrip({ holdings, kind: undefined, modelExpanded: ref<boolean>(false), width: TWO_COLUMNS });

    expect(keys(get(strip.visible))).toEqual(['kraken', 'binance', 'bitstamp', 'gemini']);
    expect(get(strip.hiddenCount)).toBe(2);
    expect(get(strip.hiddenValue).toFixed()).toBe('30');
    expect(get(strip.canExpand)).toBe(true);
  });

  it('should show every tile once expanded, and keep the toggle', () => {
    const strip = useLocationsStrip({ holdings, kind: undefined, modelExpanded: ref<boolean>(true), width: TWO_COLUMNS });

    expect(get(strip.visible)).toHaveLength(6);
    expect(get(strip.hiddenCount)).toBe(0);
    expect(get(strip.canExpand)).toBe(true);
  });

  it('should narrow to the chosen kind and measure shares against that kind', () => {
    const strip = useLocationsStrip({ holdings, kind: SourceKind.MANUAL, modelExpanded: ref<boolean>(false), width: TWO_COLUMNS });

    expect(keys(get(strip.visible))).toEqual(['kraken']);
    expect(get(strip.visible)[0].value.toFixed()).toBe('5');
    expect(get(strip.base).toFixed()).toBe('5');
    expect(get(strip.canExpand)).toBe(false);
  });

  it('should follow the width as the grid resizes', () => {
    const width = ref<number>(TWO_COLUMNS);
    const strip = useLocationsStrip({ holdings, kind: undefined, modelExpanded: ref<boolean>(false), width });

    set(width, 1000);

    expect(get(strip.visible)).toHaveLength(6);
    expect(get(strip.canExpand)).toBe(false);
  });
});
