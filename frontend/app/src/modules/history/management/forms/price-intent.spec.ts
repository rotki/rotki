import { beforeEach, describe, expect, it, vi } from 'vitest';
import { collectPriceIntents, type PriceIntent, type PriceIntentCarrier, usePriceIntents } from '@/modules/history/management/forms/price-intent';

const { mockUpdatePrice } = vi.hoisted(() => ({ mockUpdatePrice: vi.fn() }));

vi.mock('@/modules/history/events/prices/use-event-price-update', () => ({
  useEventPriceUpdate: (): unknown => ({ updatePrice: mockUpdatePrice }),
}));

const ethIntent: PriceIntent = {
  fromAsset: 'ETH',
  price: '2000',
  timestampMs: 1742901211000,
  toAsset: 'USD',
};

const usdcIntent: PriceIntent = {
  fromAsset: 'USDC',
  price: '1',
  timestampMs: 1742901211000,
  toAsset: 'USD',
};

describe('collectPriceIntents', () => {
  it('should return nothing when no row has a pending price', () => {
    const rows: PriceIntentCarrier[] = [{}, {}];

    expect(collectPriceIntents(rows, [])).toEqual([]);
  });

  it('should gather the intents of every group in render order', () => {
    expect(collectPriceIntents([{ priceIntent: ethIntent }], [{}, { priceIntent: usdcIntent }]))
      .toEqual([ethIntent, usdcIntent]);
  });

  it('should skip the rows in between that have nothing to write', () => {
    expect(collectPriceIntents([{}, { priceIntent: ethIntent }, {}])).toEqual([ethIntent]);
  });
});

describe('runPriceIntents', () => {
  beforeEach(() => {
    mockUpdatePrice.mockClear().mockResolvedValue(undefined);
  });

  it('should write nothing when there is nothing pending', async () => {
    const { runPriceIntents } = usePriceIntents();

    await expect(runPriceIntents([])).resolves.toEqual({ success: true });
    expect(mockUpdatePrice).not.toHaveBeenCalled();
  });

  it('should write each intent as a manual price', async () => {
    const { runPriceIntents } = usePriceIntents();

    await expect(runPriceIntents([ethIntent, usdcIntent])).resolves.toEqual({ success: true });

    expect(mockUpdatePrice).toHaveBeenCalledTimes(2);
    expect(mockUpdatePrice).toHaveBeenNthCalledWith(1, { ...ethIntent, mode: 'manual' });
    expect(mockUpdatePrice).toHaveBeenNthCalledWith(2, { ...usdcIntent, mode: 'manual' });
  });

  it('should stop at the first failure so the event is not saved either', async () => {
    mockUpdatePrice.mockRejectedValueOnce(new Error('nope'));
    const { runPriceIntents } = usePriceIntents();

    const status = await runPriceIntents([ethIntent, usdcIntent]);

    expect(status).toEqual({ message: 'nope', success: false });
    // The second intent is never attempted.
    expect(mockUpdatePrice).toHaveBeenCalledTimes(1);
  });
});
