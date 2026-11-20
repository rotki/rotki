import { bigNumberify } from '@rotki/common';
import { I18nTStub } from '@test/stubs/I18nT';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import DataIssueBalanceMismatchSummary from '@/modules/history/data-issues/components/DataIssueBalanceMismatchSummary.vue';

const { shouldShowAmount, symbol } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    shouldShowAmount: ref<boolean>(true),
    symbol: ref<string>('ETH'),
  };
});

vi.mock('@/modules/assets/amount-display', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    useAmountDisplaySettings: (): Record<string, unknown> => ({ shouldShowAmount }),
  };
});

vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { useAssetField: () => Ref<string> } => ({ useAssetField: () => symbol }),
}));

const stubs = {
  AmountDiffDisplay: {
    props: ['amount', 'reference', 'decimals'],
    template: '<span :data-reference="reference.toString()" :data-decimals="decimals">{{ amount.toString() }}</span>',
  },
  AssetAmountDisplay: {
    props: ['amount', 'asset', 'decimals', 'noCollectionParent'],
    template: '<span :data-asset="asset" :data-decimals="decimals" :data-no-collection-parent="String(Boolean(noCollectionParent))">{{ amount.toString() }}</span>',
  },
  I18nT: I18nTStub,
};

function createWrapper(overrides: {
  accruedInterest?: ReturnType<typeof bigNumberify>;
  delta?: ReturnType<typeof bigNumberify>;
  derived?: ReturnType<typeof bigNumberify>;
  observed?: ReturnType<typeof bigNumberify>;
} = {}): VueWrapper {
  return mount(DataIssueBalanceMismatchSummary, {
    global: { stubs },
    props: {
      asset: 'eip155:1/erc20:0x0',
      delta: bigNumberify('-0.010001337009133413'),
      derived: bigNumberify('0.10041049160120971'),
      observed: bigNumberify('0.090409712150987558'),
      ...overrides,
    },
  });
}

describe('dataIssueBalanceMismatchSummary', () => {
  beforeEach(() => {
    set(shouldShowAmount, true);
  });

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

  it('should display accrued interest under the tracked balance without pinning decimals', () => {
    const wrapper = createWrapper({ accruedInterest: bigNumberify('0.00525') });

    const interest = wrapper.get('[data-testid="data-issue-mismatch-accrued-interest"]');
    expect(interest.find('[keypath="data_issues.accrued_interest"]').exists()).toBe(true);
    expect(interest.text()).toContain('+');
    expect(interest.text()).toContain('0.00525');
    const interestAmount = interest.get('[data-asset]');
    expect(interestAmount.attributes('data-decimals')).toBeUndefined();
    expect(interestAmount.attributes('data-no-collection-parent')).toBe('true');
  });

  it('should fall back to user precision for 78-decimal ray-derived accrued interest and delta', () => {
    const rayAccruedInterest = bigNumberify('46.4638039999999999999999900379158777898096267801723634815456113170195509546138');
    const rayDelta = bigNumberify('500.0000000000000000000000099620841222101903732198276365184543886829804490453862');
    const wrapper = createWrapper({
      accruedInterest: rayAccruedInterest,
      delta: rayDelta,
      derived: bigNumberify('14004.209174'),
      observed: bigNumberify('14550.672978'),
    });

    const interest = wrapper.get('[data-testid="data-issue-mismatch-accrued-interest"]');
    expect(interest.get('[data-asset]').attributes('data-decimals')).toBeUndefined();
    expect(wrapper.get('[data-testid=data-issue-mismatch-delta]').attributes('data-decimals')).toBeUndefined();
  });

  it('should omit the leading plus sign on accrued interest when privacy mode hides amounts', () => {
    set(shouldShowAmount, false);
    const wrapper = createWrapper({ accruedInterest: bigNumberify('0.00525') });

    const interest = wrapper.get('[data-testid="data-issue-mismatch-accrued-interest"]');
    expect(interest.text()).not.toContain('+');
  });

  it('should omit accrued interest when absent or zero', () => {
    expect(createWrapper().find('[data-testid="data-issue-mismatch-accrued-interest"]').exists()).toBe(false);
    expect(createWrapper({ accruedInterest: bigNumberify('0') }).find('[data-testid="data-issue-mismatch-accrued-interest"]').exists()).toBe(false);
  });
});
