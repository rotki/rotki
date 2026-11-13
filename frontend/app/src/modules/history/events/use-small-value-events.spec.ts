import { type BigNumber, bigNumberify, NoPrice, Zero } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { isBelowThreshold, useSmallValueEvents } from '@/modules/history/events/use-small-value-events';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const getHistoricPrice = vi.hoisted(() => vi.fn<(fromAsset: string, timestamp: number) => BigNumber>());

vi.mock('@/modules/assets/prices/use-historic-price-cache', () => ({
  useHistoricPriceCache: (): Record<string, unknown> => ({ getHistoricPrice }),
}));

const event = { amount: bigNumberify(2), asset: 'ETH', timestamp: 1_700_000_000_123 };

describe('isBelowThreshold', () => {
  it('should count a priced value under the threshold as small', () => {
    expect(isBelowThreshold(bigNumberify(0.4), bigNumberify(0.8), 1)).toBe(true);
  });

  it('should not count a value at the threshold as small', () => {
    expect(isBelowThreshold(bigNumberify(0.5), bigNumberify(1), 1)).toBe(false);
  });

  it('should not classify a value whose price is still loading or missing', () => {
    expect(isBelowThreshold(NoPrice, NoPrice.multipliedBy(2), 1)).toBe(false);
    expect(isBelowThreshold(Zero, Zero, 1)).toBe(false);
  });

  it('should count a zero amount at a known price as small', () => {
    expect(isBelowThreshold(bigNumberify(2000), Zero, 1)).toBe(true);
  });
});

describe('useSmallValueEvents', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    getHistoricPrice.mockReset();
  });

  it('should price nothing while the setting is off', () => {
    getHistoricPrice.mockReturnValue(bigNumberify(0.1));
    const { enabled, isSmallValue } = useSmallValueEvents();

    expect(get(enabled)).toBe(false);
    expect(isSmallValue(event)).toBe(false);
    expect(getHistoricPrice).not.toHaveBeenCalled();
  });

  it('should price the event at its timestamp in seconds once the setting is on', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true });
    getHistoricPrice.mockReturnValue(bigNumberify(0.1));
    const { isSmallValue } = useSmallValueEvents();

    expect(isSmallValue(event)).toBe(true);
    expect(getHistoricPrice).toHaveBeenCalledWith('ETH', 1_700_000_000);
  });

  it('should compare the value of the whole amount against the configured threshold', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true, smallValueEventThreshold: 5 });
    getHistoricPrice.mockReturnValue(bigNumberify(2));
    const { isSmallValue, threshold } = useSmallValueEvents();

    expect(get(threshold)).toBe(5);
    expect(isSmallValue(event)).toBe(true);
    expect(isSmallValue({ ...event, amount: bigNumberify(3) })).toBe(false);
  });

  it('should keep an event whose price is not resolved yet', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true });
    getHistoricPrice.mockReturnValue(NoPrice);
    const { isSmallValue } = useSmallValueEvents();

    expect(isSmallValue(event)).toBe(false);
  });

  it('should not price an event without a timestamp', () => {
    useSettingsRepo().updateFrontend({ deemphasizeSmallValueEvents: true });
    const { isSmallValue } = useSmallValueEvents();

    expect(isSmallValue({ ...event, timestamp: 0 })).toBe(false);
    expect(getHistoricPrice).not.toHaveBeenCalled();
  });
});
