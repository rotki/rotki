import type { LocationLabel } from '@/modules/core/common/location';
import { get } from '@vueuse/core';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useHistoryStore } from '@/modules/history/use-history-store';
import { useLocationLabels } from '@/modules/history/use-location-labels';

const mockGetAddressName = vi.fn();

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    allTxChainsInfo: ref([{ id: 'eth' }]),
    matchChain: (location: string): string | undefined => ['eth', 'ethereum'].includes(location) ? 'eth' : undefined,
  }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName: mockGetAddressName }),
}));

function trackAccount(overrides: Record<string, unknown> = {}): void {
  useBlockchainAccountsStore().updateAccounts('eth', [{
    chain: 'eth',
    data: { address: '0xA', type: 'address' },
    label: 'Main wallet',
    nativeAsset: 'ETH',
    tags: ['defi'],
    ...overrides,
  }]);
}

const item: LocationLabel = { location: 'eth', locationLabel: '0xA' };

describe('useLocationLabels', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockGetAddressName.mockReset();
    mockGetAddressName.mockReturnValue(undefined);
  });

  it('should use the provided options and fall back to the store labels', () => {
    const provided: LocationLabel[] = [{ location: 'eth', locationLabel: '0xA' }];
    const { locationLabelOptions } = useLocationLabels(ref(provided));
    expect(get(locationLabelOptions)).toStrictEqual(provided);

    useHistoryStore().setLocationLabels([{ location: 'eth', locationLabel: '0xB' }]);
    const { locationLabelOptions: fromStore } = useLocationLabels(ref(undefined));
    expect(get(fromStore)).toStrictEqual([{ location: 'eth', locationLabel: '0xB' }]);
  });

  it('should resolve only tx-chain locations', () => {
    const { getBlockchainLocation } = useLocationLabels(ref(undefined));
    expect(getBlockchainLocation('eth')).toBe('eth');
    expect(getBlockchainLocation('unknown')).toBeUndefined();
  });

  it('should not send an exchange location to address resolution', () => {
    const exchangeItem: LocationLabel = { location: 'kraken', locationLabel: 'Kraken 1' };
    const { getAccountName, isAccountNamePending } = useLocationLabels(ref(undefined));

    expect(getAccountName(exchangeItem)).toBeUndefined();
    expect(isAccountNamePending(exchangeItem)).toBe(false);
    expect(mockGetAddressName).not.toHaveBeenCalled();
  });

  it('should expose the tags and tracked label of a registered account', () => {
    trackAccount();
    const { getTags, getTrackedAccountLabel } = useLocationLabels(ref(undefined));

    expect(getTags(item)).toStrictEqual(['defi']);
    expect(getTrackedAccountLabel(item)).toBe('Main wallet');
  });

  it('should not report a tracked label that just repeats the address', () => {
    trackAccount({ label: '0xA' });
    const { getTrackedAccountLabel } = useLocationLabels(ref(undefined));

    expect(getTrackedAccountLabel(item)).toBeUndefined();
  });

  it('should prefer the tracked label, then the address-book name, for the display name', () => {
    trackAccount();
    const { getAccountName } = useLocationLabels(ref(undefined));
    expect(getAccountName(item)).toBe('Main wallet');

    setActivePinia(createPinia());
    mockGetAddressName.mockReturnValue('vitalik.eth');
    const { getAccountName: fromAddressBook } = useLocationLabels(ref(undefined));
    expect(fromAddressBook(item)).toBe('vitalik.eth');
  });

  it('should match by address, resolved name, tracked label and tags', () => {
    trackAccount();
    mockGetAddressName.mockReturnValue('vitalik.eth');
    const { filter } = useLocationLabels(ref(undefined));

    expect(filter(item, '0xa')).toBe(true);
    expect(filter(item, 'vitalik')).toBe(true);
    expect(filter(item, 'main')).toBe(true);
    expect(filter(item, 'defi')).toBe(true);
    expect(filter(item, 'nope')).toBe(false);
  });
});
