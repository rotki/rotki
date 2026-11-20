import type { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import type { ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import { bigNumberify, Blockchain } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { IssueKind } from '@/modules/history/data-issues/constants';
import ReconciliationStatusCell from '@/modules/history/reconciliation/components/ReconciliationStatusCell.vue';

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): ReturnType<typeof useSupportedChains> => createMock<ReturnType<typeof useSupportedChains>>({
    matchChain: (location: string) => (location === 'ethereum' ? Blockchain.ETH : undefined),
  }),
}));

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { type: [Object, String], required: true } },
  template: '<a><slot /></a>',
});

function bucket(overrides: Partial<ReconciliationBucket> = {}): ReconciliationBucket {
  return {
    asset: 'ETH',
    check: null,
    derivedBalance: null,
    issueId: null,
    issueKind: null,
    lastEventTs: null,
    observedAt: null,
    observedBalance: null,
    protocol: null,
    reasons: [],
    status: 'pending',
    stop: null,
    ...overrides,
  };
}

function mountCell(
  value: ReconciliationBucket,
  props: { location?: string; locationLabel?: string | null } = {},
): VueWrapper {
  return mount(ReconciliationStatusCell, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'RouterLink': RouterLinkStub,
        'i18n-t': { template: '<span class="i18n-t"><slot name="date" /><slot /></span>' },
      },
    },
    props: { bucket: value, ...props },
  });
}

describe('reconciliation status cell', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should explain a pending bucket with the most actionable reason', () => {
    const wrapper = mountCell(bucket({
      reasons: ['history_not_synced', 'derived_history_stale'],
      status: 'pending',
    }));

    expect(wrapper.text()).toContain('data_issues.reconciliation.reason.history_not_synced');
  });

  it('should pick the mismatch sentence from the sign and offer the issue link', async () => {
    const wrapper = mountCell(bucket({
      check: {
        comparedAt: 1,
        delta: bigNumberify('-1'),
        derivedBalance: bigNumberify('2'),
        observedAt: 1,
        observedBalance: bigNumberify('1'),
      },
      issueId: 7,
      status: 'mismatch',
    }));

    expect(wrapper.text()).toContain('data_issues.reconciliation.reason.mismatch_lower');
    await wrapper.find('[data-testid="reconciliation-open-issue"]').trigger('click');
    expect(wrapper.emitted('open-issue')?.[0]).toStrictEqual([7]);
  });

  it('should offer spam only for a token held with no events', () => {
    const token = mountCell(bucket({
      asset: 'eip155:1/erc20:0xabc',
      observedBalance: bigNumberify('5'),
      status: 'mismatch',
    }));
    const native = mountCell(bucket({
      asset: 'ETH',
      observedBalance: bigNumberify('5'),
      status: 'mismatch',
    }));

    expect(token.find('[data-testid="reconciliation-mark-spam"]').exists()).toBe(true);
    expect(native.find('[data-testid="reconciliation-mark-spam"]').exists()).toBe(false);
  });

  it('should keep the event link for a blocked bucket without an issue', () => {
    const wrapper = mountCell(bucket({
      status: 'blocked',
      stop: {
        derivedBalanceBeforeEvent: bigNumberify('0.5'),
        eventIdentifier: 1234,
        eventTimestamp: 1_700_000_000_000,
        groupIdentifier: '0xgroup',
        negativeAmount: bigNumberify('-1'),
      },
    }));

    expect(wrapper.find('[data-testid="reconciliation-view-event"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="reconciliation-open-issue"]').exists()).toBe(false);
    expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
      name: '/history/events/',
      query: {
        asset: 'ETH',
        highlightedNegativeBalanceEvent: '1234',
        targetGroupIdentifier: '0xgroup',
      },
    });
  });

  it('should not offer a view-event link for a stop whose event was deleted, as there is no group to page to', () => {
    const wrapper = mountCell(bucket({
      issueId: 7,
      status: 'blocked',
      stop: {
        derivedBalanceBeforeEvent: bigNumberify('0.5'),
        eventIdentifier: 1234,
        eventTimestamp: 1_700_000_000_000,
        groupIdentifier: null,
        negativeAmount: bigNumberify('-1'),
      },
    }));

    expect(wrapper.find('[data-testid="reconciliation-open-issue"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="reconciliation-view-event"]').exists()).toBe(false);
  });

  it('should explain a blocked row by its stop, without the observation time that does not unblock it', () => {
    const wrapper = mountCell(bucket({
      issueId: 7,
      observedAt: 1_700_000_000,
      status: 'blocked',
      stop: {
        derivedBalanceBeforeEvent: bigNumberify('1'),
        eventIdentifier: 1234,
        eventTimestamp: 1_700_000_000_000,
        groupIdentifier: 'group',
        negativeAmount: bigNumberify('-2'),
      },
    }));

    const keypaths = wrapper.findAll('i18n-t-stub').map(element => element.attributes('keypath'));
    expect(keypaths).toContain('data_issues.reconciliation.reason.blocked');
    expect(keypaths).not.toContain('data_issues.reconciliation.observed_at');
  });

  it('should explain a blocked row caused by an invalid event amount and offer the issue link', async () => {
    const wrapper = mountCell(bucket({
      issueId: 9,
      issueKind: IssueKind.INVALID_EVENT_AMOUNT,
      status: 'blocked',
      stop: {
        derivedBalanceBeforeEvent: bigNumberify('1'),
        eventIdentifier: 1234,
        eventTimestamp: 1_700_000_000_000,
        groupIdentifier: 'group',
        negativeAmount: bigNumberify('-0.5'),
      },
    }));

    const keypaths = wrapper.findAll('i18n-t-stub').map(element => element.attributes('keypath'));
    expect(keypaths).toContain('data_issues.reconciliation.reason.blocked_invalid_event_amount');
    expect(keypaths).not.toContain('data_issues.reconciliation.reason.blocked');
    await wrapper.find('[data-testid="reconciliation-open-issue"]').trigger('click');
    expect(wrapper.emitted('open-issue')?.[0]).toStrictEqual([9]);
  });

  it('should explain a blocked row without stop details in a sentence that needs none', () => {
    const wrapper = mountCell(bucket({ status: 'blocked' }));

    expect(wrapper.text()).toContain('data_issues.reconciliation.reason.blocked_without_stop');
  });

  it('should show only the comparison time for a row with a saved comparison', () => {
    const wrapper = mountCell(bucket({
      check: {
        comparedAt: 1_700_000_100,
        delta: bigNumberify('0'),
        derivedBalance: bigNumberify('1'),
        observedAt: 1_700_000_000,
        observedBalance: bigNumberify('1'),
      },
      status: 'reconciled',
    }));

    const keypaths = wrapper.findAll('i18n-t-stub').map(element => element.attributes('keypath'));
    expect(keypaths).toContain('data_issues.reconciliation.compared_at');
    expect(keypaths).not.toContain('data_issues.reconciliation.observed_at');
  });

  it('should show the observation time for a row without a saved comparison', () => {
    const wrapper = mountCell(bucket({ observedAt: 1_700_000_000, status: 'pending' }));

    const keypaths = wrapper.findAll('i18n-t-stub').map(element => element.attributes('keypath'));
    expect(keypaths).toContain('data_issues.reconciliation.observed_at');
  });

  it('should render the status icon as well as the label', () => {
    const wrapper = mountCell(bucket({ status: 'reconciled' }));

    expect(wrapper.text()).toContain('data_issues.reconciliation.status.matches');
    expect(wrapper.html()).toContain('lu-circle-check');
  });

  it('should offer a filtered View events link and Inspect trace action for non-blocked buckets', async () => {
    const value = bucket({ asset: 'eip155:1/erc20:0x6df1', status: 'pending' });
    const wrapper = mountCell(value, {
      location: 'ethereum',
      locationLabel: '0x006a3aD7251db5D12992B62cce26252ac58492Dd',
    });

    const eventsLink = wrapper.find('[data-testid="reconciliation-view-events"]');
    expect(eventsLink.exists()).toBe(true);
    expect(wrapper.findComponent(RouterLinkStub).props('to')).toEqual({
      name: '/history/events/',
      query: {
        addresses: '0x006a3aD7251db5D12992B62cce26252ac58492Dd',
        asset: 'eip155:1/erc20:0x6df1',
        location: 'ethereum',
      },
    });

    await wrapper.get('[data-testid="reconciliation-inspect-trace"]').trigger('click');
    expect(wrapper.emitted('inspect-trace')?.[0]).toStrictEqual([value]);
  });

  it('should scope exchange View events links via locationLabels instead of addresses', () => {
    const wrapper = mountCell(bucket({ asset: 'BTC', status: 'not_compared' }), {
      location: 'kraken',
      locationLabel: 'Kraken 1',
    });

    expect(wrapper.findComponent(RouterLinkStub).props('to')).toStrictEqual({
      name: '/history/events/',
      query: {
        asset: 'BTC',
        location: 'kraken',
        locationLabels: 'Kraken 1',
      },
    });
  });
});
