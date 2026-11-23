import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import AssetViewComparison from '@/modules/balances/components/AssetViewComparison.vue';

const h = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    available: ref<boolean>(true),
    comparable: ref<boolean>(true),
    getAssetComparison: vi.fn<(identifier: string, groupCollection?: boolean) => AssetComparison>(),
    getAssetField: vi.fn<(identifier: string, field: string) => string | undefined>(),
    isHistory: ref<boolean>(true),
  };
});

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ getAssetField: h.getAssetField }),
}));
vi.mock('@/modules/balances/view/use-balance-view', () => ({
  useBalanceView: (): object => ({ available: h.available }),
}));
vi.mock('@/modules/balances/view/use-balance-view-data', () => ({
  useBalanceViewData: (): object => ({
    comparable: h.comparable,
    getAssetComparison: h.getAssetComparison,
    isHistory: h.isHistory,
  }),
}));

const RouterLinkStub = { props: ['to'], template: '<a><slot /></a>' };
const AssetAmountDisplayStub = { props: ['amount', 'asset'], template: '<span>{{ amount.toFixed() }}</span>' };

function makeComparison(history: string | number, queried: string | number, manual: string | number = 0): AssetComparison {
  const delta = bigNumberify(history).minus(queried);
  return { delta, history: bigNumberify(history), manual: bigNumberify(manual), queried: bigNumberify(queried), valueDelta: delta };
}

function reconciliationTo(asset: string): object {
  return { name: '/history/data-issues/[[tab]]', params: { tab: 'reconciliation' }, query: { asset, view: 'all' } };
}

function mountComparison(props: { identifier: string; isCollectionParent?: boolean }): VueWrapper {
  return mount(AssetViewComparison, {
    global: { stubs: { AssetAmountDisplay: AssetAmountDisplayStub, RouterLink: RouterLinkStub } },
    props,
  });
}

describe('assetViewComparison', () => {
  beforeEach(() => {
    h.available.value = true;
    h.comparable.value = true;
    h.isHistory.value = true;
    h.getAssetComparison.mockReset().mockReturnValue(makeComparison('22060.97', '22067.19'));
    h.getAssetField.mockReset().mockReturnValue('USDC');
  });

  it('should link to reconciliation by asset identifier, or by symbol for a collection parent', () => {
    const assetId = 'eip155:1/erc20:0x6df1C1E379bC5a00a7b4C6e67A203333772f45A8';
    expect(mountComparison({ identifier: assetId }).getComponent(RouterLinkStub).props('to')).toEqual(reconciliationTo(assetId));
    expect(h.getAssetComparison).toHaveBeenCalledWith(assetId, false);

    const parentId = 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48';
    expect(mountComparison({ identifier: parentId, isCollectionParent: true }).getComponent(RouterLinkStub).props('to'))
      .toEqual(reconciliationTo('USDC'));
    expect(h.getAssetComparison).toHaveBeenCalledWith(parentId, true);
  });

  it('should render nothing when the balance view is unavailable or not comparable', () => {
    h.available.value = false;
    expect(mountComparison({ identifier: 'ETH' }).find('[data-testid="asset-view-comparison"]').exists()).toBe(false);

    h.available.value = true;
    h.comparable.value = false;
    expect(mountComparison({ identifier: 'ETH' }).find('[data-testid="asset-view-comparison"]').exists()).toBe(false);
  });

  it('should show queried amount in history view and history amount in live view', () => {
    const inHistory = mountComparison({ identifier: 'ETH' });
    expect(inHistory.text()).toContain('balance_view.live');
    expect(inHistory.text()).toContain('22067.19');

    h.isHistory.value = false;
    const inLive = mountComparison({ identifier: 'ETH' });
    expect(inLive.text()).toContain('balance_view.from_history');
    expect(inLive.text()).toContain('22060.97');
  });

  it('should show the delta link and manual note only when the views differ', () => {
    h.getAssetComparison.mockReturnValue(makeComparison(10, 10, 2));
    const agreeing = mountComparison({ identifier: 'ETH' });
    expect(agreeing.find('[data-testid="asset-view-comparison-delta"]').exists()).toBe(false);
    expect(agreeing.find('[data-testid="asset-view-comparison-manual"]').exists()).toBe(false);

    h.getAssetComparison.mockReturnValue(makeComparison(10, 15, 3));
    expect(mountComparison({ identifier: 'ETH' }).find('[data-testid="asset-view-comparison-manual"]').exists()).toBe(true);
  });
});
