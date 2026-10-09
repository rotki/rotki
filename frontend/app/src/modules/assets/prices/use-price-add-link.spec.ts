import type { LocationQuery } from 'vue-router';
import { describe, expect, it, vi } from 'vitest';
import { type PriceAddLink, usePriceAddLink } from '@/modules/assets/prices/use-price-add-link';

const captured = vi.hoisted(() => {
  const holder: { handler?: (query: LocationQuery) => void } = {};
  return holder;
});

vi.mock('@/modules/core/common/use-add-query', () => ({
  useAddQuery: vi.fn((onAdd: (query: LocationQuery) => void) => {
    captured.handler = onAdd;
    return { consumeAddQuery: vi.fn() };
  }),
}));

function linkFor(query: LocationQuery): PriceAddLink {
  const onAdd = vi.fn<(link: PriceAddLink) => void>();
  usePriceAddLink(onAdd);
  captured.handler?.(query);
  expect(onAdd).toHaveBeenCalledOnce();
  return onAdd.mock.calls[0][0];
}

describe('modules/assets/prices/use-price-add-link', () => {
  it('should read the asset and the time a missing-price link names', () => {
    expect(linkFor({ add: 'true', fromAsset: 'ETH', timestamp: '1700000000' }))
      .toStrictEqual({ fromAsset: 'ETH', timestamp: 1_700_000_000 });
  });

  it('should answer an empty asset and no time for a bare add link', () => {
    expect(linkFor({ add: 'true' })).toStrictEqual({ fromAsset: '', timestamp: 0 });
  });

  it('should take the first value of a repeated key', () => {
    expect(linkFor({ add: 'true', fromAsset: ['BTC', 'ETH'], timestamp: ['5', '9'] }))
      .toStrictEqual({ fromAsset: 'BTC', timestamp: 5 });
  });

  it.each(['soon', '-3', '0'])('should treat a timestamp of %s as no time', (timestamp) => {
    expect(linkFor({ add: 'true', fromAsset: 'ETH', timestamp }).timestamp).toBe(0);
  });
});
