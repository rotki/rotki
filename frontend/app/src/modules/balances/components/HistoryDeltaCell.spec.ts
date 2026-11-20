import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import HistoryDeltaCell from '@/modules/balances/components/HistoryDeltaCell.vue';

const h = vi.hoisted(() => ({
  getAssetField: vi.fn<(asset: string, field: string) => string | undefined>(),
}));

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): object => ({ getAssetField: h.getAssetField }),
}));

function comparison(history: number, queried: number, manual: number): AssetComparison {
  return {
    delta: bigNumberify(history - queried),
    history: bigNumberify(history),
    manual: bigNumberify(manual),
    queried: bigNumberify(queried),
    valueDelta: bigNumberify((history - queried) * 2),
  };
}

const RouterLinkStub = { props: ['to'], template: '<a><slot /></a>' };

function reconciliationTo(asset: string): object {
  return { name: '/history/data-issues/[[tab]]', params: { tab: 'reconciliation' }, query: { asset, view: 'all' } };
}

function mountCell(value?: AssetComparison, asset?: string, isCollectionParent?: boolean): VueWrapper {
  return mount(HistoryDeltaCell, {
    global: { stubs: { RouterLink: RouterLinkStub, ValueDisplay: true } },
    props: { asset, comparison: value, isCollectionParent },
  });
}

describe('historyDeltaCell', () => {
  beforeEach(() => {
    h.getAssetField.mockReset().mockReturnValue('USDC');
  });

  it('should render nothing when history and queried agree', () => {
    expect(mountCell(comparison(15, 15, 3)).find('[data-testid="history-delta-cell"]').exists()).toBe(false);
  });

  it('should render nothing without a comparison', () => {
    expect(mountCell().find('[data-testid="history-delta-cell"]').exists()).toBe(false);
  });

  it('should name the manual amount behind part of the gap', () => {
    const wrapper = mountCell(comparison(15, 25, 3));

    expect(wrapper.find('[data-testid="history-delta-cell-manual"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="history-delta-cell-all-manual"]').exists()).toBe(false);
  });

  it('should say the gap is all manual when every queried unit is manual', () => {
    const wrapper = mountCell(comparison(0, 1.5, 1.5));

    expect(wrapper.find('[data-testid="history-delta-cell-all-manual"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="history-delta-cell-manual"]').exists()).toBe(false);
  });

  it('should show only the difference when no manual balance is involved', () => {
    const wrapper = mountCell(comparison(500, 0, 0));

    expect(wrapper.find('[data-testid="history-delta-cell"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="history-delta-cell-manual"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="history-delta-cell-all-manual"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="history-delta-cell-link"]').exists()).toBe(false);
  });

  it('should link to reconciliation by asset identifier, or by symbol for a folded collection parent', () => {
    expect(mountCell(comparison(10, 16, 0), 'eip155:1/erc20:0x6df1').getComponent(RouterLinkStub).props('to'))
      .toEqual(reconciliationTo('eip155:1/erc20:0x6df1'));
    expect(mountCell(comparison(10, 16, 0), 'eip155:1/erc20:0xA0b8', true).getComponent(RouterLinkStub).props('to'))
      .toEqual(reconciliationTo('USDC'));
  });

  it('should stop click propagation on the reconciliation link so parent row clicks do not fire', async () => {
    const onParentClick = vi.fn<() => void>();
    const Host = defineComponent({
      components: { HistoryDeltaCell },
      setup() {
        return { comparison: comparison(10, 16, 0), onParentClick };
      },
      template: '<div @click="onParentClick"><HistoryDeltaCell asset="ETH" :comparison="comparison" /></div>',
    });

    const wrapper = mount(Host, {
      global: { stubs: { RouterLink: RouterLinkStub, ValueDisplay: true } },
    });

    await wrapper.get('[data-testid="history-delta-cell-link"]').trigger('click');

    expect(onParentClick).not.toHaveBeenCalled();
  });
});
