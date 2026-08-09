import type { AddressData, AssetBreakdown, BlockchainAccount } from '@/modules/accounts/blockchain-accounts';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mockUseSupportedChains } from '@test/utils/mocks/supported-chains';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAssetLocationsData } from './use-asset-locations-data';

const { spies } = vi.hoisted(() => ({
  spies: {
    getAssetBreakdown: vi.fn(),
    getAccountByAddress: vi.fn(),
    getAddressName: vi.fn(),
    getAssetPriceInfo: vi.fn(),
    getChainName: vi.fn(),
    matchChain: vi.fn(),
    getAccountAddress: vi.fn((account: { data: { address: string } }) => account.data.address),
  },
}));

const currencySymbol = ref<string>('USD');

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => currencySymbol),
}));
vi.mock('@/modules/accounts/use-blockchain-accounts-store', () => ({
  useBlockchainAccountsStore: (): object => ({ getAccountByAddress: spies.getAccountByAddress }),
}));
vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName: spies.getAddressName }),
}));
vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: (): object => ({ getAssetPriceInfo: spies.getAssetPriceInfo }),
}));
vi.mock('@/modules/core/common/use-supported-chains', () =>
  mockUseSupportedChains({ getChainName: spies.getChainName, matchChain: spies.matchChain }));
vi.mock('@/modules/balances/use-asset-balances-breakdown', () => ({
  useAssetBalancesBreakdown: (): object => ({ getAssetBreakdown: spies.getAssetBreakdown }),
}));
vi.mock('@/modules/accounts/account-utils', () => ({
  getAccountAddress: spies.getAccountAddress,
}));

function breakdown(overrides: Partial<AssetBreakdown>): AssetBreakdown {
  return { address: '0xabc', amount: bigNumberify(1), location: 'ethereum', value: bigNumberify(100), ...overrides };
}

function options(over: Partial<Parameters<typeof useAssetLocationsData>[0]> = {}): Parameters<typeof useAssetLocationsData>[0] {
  return {
    identifier: 'ETH',
    locationFilter: ref(''),
    onlyTags: ref([]),
    selectedAccounts: ref([]),
    ...over,
  };
}

describe('useAssetLocationsData', () => {
  beforeEach(() => {
    // `useBalancesLoading` reads hydration liveness off a pinia store now that hydration is not
    // an activity the orchestrator can report on.
    setActivePinia(createPinia());
    spies.getAssetPriceInfo.mockReturnValue({ value: bigNumberify(500) });
    spies.getAccountByAddress.mockReturnValue({ label: 'My Account' });
    spies.getAddressName.mockReturnValue(null);
    spies.getChainName.mockImplementation((location: string) => location);
    spies.getAssetBreakdown.mockReturnValue([breakdown({})]);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should expose the asset total value', () => {
    const { totalValue } = useAssetLocationsData(options());
    expect(get(totalValue)).toEqual(bigNumberify(500));
  });

  it('should attach the account and its label to each breakdown', () => {
    const { assetLocations } = useAssetLocationsData(options());
    const locations = get(assetLocations);
    expect(locations).toHaveLength(1);
    expect(spies.getAccountByAddress).toHaveBeenCalledWith('0xabc', 'ethereum');
    expect(locations[0].label).toBe('My Account');
  });

  it('should filter visible locations by tag', () => {
    spies.getAssetBreakdown.mockReturnValue([
      breakdown({ address: '0x1', tags: ['tag-a'] }),
      breakdown({ address: '0x2', tags: ['tag-b'] }),
    ]);
    const { visibleAssetLocations } = useAssetLocationsData(options({ onlyTags: ref(['tag-a']) }));
    expect(get(visibleAssetLocations).map(l => l.address)).toEqual(['0x1']);
  });

  it('should filter visible locations by location name', () => {
    spies.getAssetBreakdown.mockReturnValue([
      breakdown({ address: '0x1', location: 'ethereum' }),
      breakdown({ address: '0x2', location: 'gnosis' }),
    ]);
    spies.getChainName.mockImplementation((location: string) => location === 'ethereum' ? 'Ethereum' : 'Gnosis');
    const { visibleAssetLocations } = useAssetLocationsData(options({ locationFilter: ref('ethereum') }));
    expect(get(visibleAssetLocations).map(l => l.address)).toEqual(['0x1']);
  });

  it('should filter visible locations by selected account', () => {
    spies.getAssetBreakdown.mockReturnValue([
      breakdown({ address: '0x1' }),
      breakdown({ address: '0x2' }),
    ]);
    const account = createMock<BlockchainAccount<AddressData>>({ data: { address: '0x2' } });
    const { visibleAssetLocations } = useAssetLocationsData(options({ selectedAccounts: ref([account]) }));
    expect(get(visibleAssetLocations).map(l => l.address)).toEqual(['0x2']);
  });
});
