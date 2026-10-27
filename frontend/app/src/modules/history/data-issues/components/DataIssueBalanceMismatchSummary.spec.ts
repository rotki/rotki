import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import DataIssueBalanceMismatchSummary from '@/modules/history/data-issues/components/DataIssueBalanceMismatchSummary.vue';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { useAssetField: () => Ref<string> } => ({ useAssetField: () => ref<string>('ETH') }),
}));

const stubs = {
  AmountDiffDisplay: {
    props: ['amount', 'reference', 'decimals'],
    template: '<span :data-reference="reference.toString()" :data-decimals="decimals">{{ amount.toString() }}</span>',
  },
  AssetAmountDisplay: {
    props: ['amount', 'asset', 'decimals'],
    template: '<span :data-asset="asset" :data-decimals="decimals">{{ amount.toString() }}</span>',
  },
};

function createWrapper(): VueWrapper {
  return mount(DataIssueBalanceMismatchSummary, {
    global: { stubs },
    props: {
      asset: 'eip155:1/erc20:0x0',
      delta: bigNumberify('-0.010001337009133413'),
      derived: bigNumberify('0.10041049160120971'),
      observed: bigNumberify('0.090409712150987558'),
    },
  });
}

describe('dataIssueBalanceMismatchSummary', () => {
  it('should compare each balance against the other at one shared precision', () => {
    const wrapper = createWrapper();

    const tracked = wrapper.get('[data-testid=data-issue-mismatch-tracked]');
    const onchain = wrapper.get('[data-testid=data-issue-mismatch-onchain]');
    expect(tracked.text()).toBe('0.10041049160120971');
    expect(tracked.attributes('data-reference')).toBe('0.090409712150987558');
    expect(onchain.attributes('data-reference')).toBe('0.10041049160120971');
    expect(tracked.attributes('data-decimals')).toBe('18');
    expect(onchain.attributes('data-decimals')).toBe('18');
  });

  it('should show the difference in full precision with its asset', () => {
    const wrapper = createWrapper();

    const delta = wrapper.get('[data-testid=data-issue-mismatch-delta]');
    expect(delta.text()).toBe('-0.010001337009133413');
    expect(delta.attributes('data-asset')).toBe('eip155:1/erc20:0x0');
    expect(delta.attributes('data-decimals')).toBe('18');
  });

  it('should name the asset by its symbol in the likely cause', () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain('data_issues.detail.mismatch_cause');
    expect(wrapper.text()).toContain('ETH');
  });
});
