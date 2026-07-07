import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNftPriceManagement } from './use-nft-price-management';

const { spies } = vi.hoisted(() => ({
  spies: {
    notifyError: vi.fn(),
    deleteLatestPrice: vi.fn(),
    show: vi.fn(),
  },
}));

vi.mock('@/modules/core/notifications/use-notifications', async () => {
  const actual = await vi.importActual<typeof import('@/modules/core/notifications/use-notifications')>('@/modules/core/notifications/use-notifications');
  return { ...actual, useNotifications: (): object => ({ notifyError: spies.notifyError }) };
});
vi.mock('@/modules/assets/api/use-asset-prices-api', () => ({
  useAssetPricesApi: (): object => ({ deleteLatestPrice: spies.deleteLatestPrice }),
}));
vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show: spies.show }),
}));

function nftBalance(): NonFungibleBalance {
  return createMock<NonFungibleBalance>({ id: 'nft-1', name: 'Cool NFT', priceAsset: 'ETH', priceInAsset: bigNumberify(2) });
}

describe('useNftPriceManagement', () => {
  const fetchData = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    spies.deleteLatestPrice.mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it('should delete a price and refresh', async () => {
    await useNftPriceManagement(fetchData).deletePrice(nftBalance());
    expect(spies.deleteLatestPrice).toHaveBeenCalledWith('nft-1');
    expect(fetchData).toHaveBeenCalledOnce();
  });

  it('should notify when deletion fails', async () => {
    spies.deleteLatestPrice.mockRejectedValue(new Error('boom'));
    await useNftPriceManagement(fetchData).deletePrice(nftBalance());
    expect(spies.notifyError).toHaveBeenCalledOnce();
  });

  it('should populate the price form and open the dialog', () => {
    const { customPrice, openPriceDialog, setPriceForm } = useNftPriceManagement(fetchData);
    setPriceForm(nftBalance());
    expect(get(customPrice)).toEqual({ fromAsset: 'nft-1', price: '2', toAsset: 'ETH' });
    expect(get(openPriceDialog)).toBe(true);
  });

  it('should delete through the confirmation dialog', async () => {
    useNftPriceManagement(fetchData).showDeleteConfirmation(nftBalance());
    expect(spies.show).toHaveBeenCalledOnce();
    await spies.show.mock.calls[0][1]();
    expect(spies.deleteLatestPrice).toHaveBeenCalledWith('nft-1');
  });
});
