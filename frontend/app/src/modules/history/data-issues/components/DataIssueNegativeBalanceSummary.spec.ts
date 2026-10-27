import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import DataIssueNegativeBalanceSummary from '@/modules/history/data-issues/components/DataIssueNegativeBalanceSummary.vue';

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { useAssetField: (identifier: () => string | undefined) => ComputedRef<string> } => ({
    useAssetField: identifier => computed<string>(() => (toValue(identifier) ? 'ETH' : '')),
  }),
}));

const stubs = {
  AssetAmountDisplay: {
    props: { amount: { required: true, type: Object }, asset: { default: undefined, type: String }, decimals: { default: undefined, type: Number } },
    template: '<span :data-asset="asset" :data-decimals="decimals">{{ amount.toString() }}</span>',
  },
};

function createWrapper(props: { before?: string; untrackedExchange?: boolean; asset?: string } = {}): VueWrapper {
  return mount(DataIssueNegativeBalanceSummary, {
    global: { stubs },
    props: {
      after: bigNumberify('-0.0000577953366'),
      asset: 'asset' in props ? props.asset : 'eip155:1/erc20:0x0',
      before: bigNumberify(props.before ?? '0.25'),
      untrackedExchange: props.untrackedExchange ?? false,
    },
  });
}

describe('dataIssueNegativeBalanceSummary', () => {
  it('should show the balance after the event in full precision with its asset', () => {
    const after = createWrapper().get('[data-testid=data-issue-negative-after]');

    expect(after.text()).toBe('-0.0000577953366');
    expect(after.attributes('data-asset')).toBe('eip155:1/erc20:0x0');
    expect(after.attributes('data-decimals')).toBe('13');
  });

  it('should show the balance before the event at its own precision', () => {
    const before = createWrapper().get('[data-testid=data-issue-negative-before]');

    expect(before.text()).toBe('0.25');
    expect(before.attributes('data-decimals')).toBe('2');
  });

  it('should leave a zero balance before the event at the user precision', () => {
    const before = createWrapper({ before: '0' }).get('[data-testid=data-issue-negative-before]');

    expect(before.attributes('data-decimals')).toBeUndefined();
  });

  it('should name a missing earlier transaction of the asset as the likely cause', () => {
    const cause = createWrapper().get('[data-testid=data-issue-negative-cause]');

    expect(cause.text()).toBe('data_issues.detail.negative_balance_cause::ETH');
  });

  it('should point an untracked exchange withdrawal at its own remedy', () => {
    const cause = createWrapper({ untrackedExchange: true }).get('[data-testid=data-issue-negative-cause]');

    expect(cause.text()).toBe('data_issues.detail.untracked_exchange_cause');
  });

  it('should drop the asset cause when the issue has no asset', () => {
    const wrapper = createWrapper({ asset: undefined });

    expect(wrapper.find('[data-testid=data-issue-negative-cause]').exists()).toBe(false);
  });
});
