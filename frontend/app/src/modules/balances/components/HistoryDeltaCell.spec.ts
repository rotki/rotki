import type { AssetComparison } from '@/modules/balances/view/history-comparison';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import HistoryDeltaCell from '@/modules/balances/components/HistoryDeltaCell.vue';

function comparison(history: number, queried: number, manual: number): AssetComparison {
  return {
    delta: bigNumberify(history - queried),
    history: bigNumberify(history),
    manual: bigNumberify(manual),
    queried: bigNumberify(queried),
    valueDelta: bigNumberify((history - queried) * 2),
  };
}

function mountCell(value?: AssetComparison): VueWrapper {
  return mount(HistoryDeltaCell, {
    global: { stubs: { ValueDisplay: true } },
    props: { comparison: value },
  });
}

describe('historyDeltaCell', () => {
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
  });
});
