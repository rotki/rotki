import { bigNumberify } from '@rotki/common';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetValueRow from '@/modules/assets/AssetValueRow.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

const { spies } = vi.hoisted(() => ({
  spies: {
    deletePrice: vi.fn<(payload: { fromAsset: string }) => Promise<void>>(),
  },
}));

vi.mock('@/modules/assets/prices/use-latest-price-manager', () => ({
  useLatestPrices: (): object => ({
    deletePrice: spies.deletePrice,
    refreshCurrentPrices: vi.fn(),
    refreshing: ref<boolean>(false),
  }),
}));

vi.mock('@/modules/balances/view/use-balance-view-data', () => ({
  useBalanceViewData: (): object => ({
    getAssetPriceInfo: (): object => ({
      amount: bigNumberify(1),
      price: bigNumberify(2),
      value: bigNumberify(2),
    }),
  }),
}));

vi.mock('@/modules/assets/prices/use-price-utils', () => ({
  usePriceUtils: (): object => ({
    useAssetPrice: (): object => computed(() => bigNumberify(2)),
    useIsManualAssetPrice: (): object => computed<boolean>(() => true),
  }),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({
    getAssetField: (): string => 'Ether',
  }),
}));

vi.mock('@/modules/assets/prices/use-price-refresh', () => ({
  usePriceRefresh: (): object => ({ refreshPrice: vi.fn(), refreshing: ref<boolean>(false) }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): object => ref<string>('USD'),
}));

function createWrapper(): VueWrapper<InstanceType<typeof AssetValueRow>> {
  return mount(AssetValueRow, {
    global: {
      stubs: {
        AssetAmountDisplay: true,
        AssetValueDisplay: true,
        AssetViewComparison: true,
        FiatDisplay: true,
        LatestPriceFormDialog: true,
        RowActions: true,
      },
    },
    props: { identifier: 'ETH' },
  });
}

describe('assetValueRow', () => {
  beforeEach(() => {
    spies.deletePrice.mockResolvedValue(undefined);
  });

  it('should have the price ask, naming the asset, before its custom price is deleted', () => {
    const wrapper = createWrapper();

    expect(wrapper.findComponent(RowActions).props('deleteConfirm')).toStrictEqual({
      message: 'assets.custom_price.delete.message::Ether',
      title: 'assets.custom_price.delete.tooltip',
    });
    expect(spies.deletePrice).not.toHaveBeenCalled();
  });

  it('should delete the custom price of this asset once confirmed', async () => {
    const wrapper = createWrapper();

    wrapper.findComponent(RowActions).vm.$emit('delete-click');
    await flushPromises();

    expect(spies.deletePrice).toHaveBeenCalledExactlyOnceWith({ fromAsset: 'ETH' });
  });
});
