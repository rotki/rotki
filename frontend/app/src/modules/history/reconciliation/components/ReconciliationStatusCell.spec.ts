import type { ReconciliationBucket } from '@/modules/history/reconciliation/schemas';
import { bigNumberify } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import ReconciliationStatusCell from '@/modules/history/reconciliation/components/ReconciliationStatusCell.vue';

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

function mountCell(value: ReconciliationBucket): VueWrapper {
  return mount(ReconciliationStatusCell, {
    global: {
      plugins: [createPinia()],
      stubs: {
        'RouterLink': RouterLinkStub,
        'i18n-t': { template: '<span class="i18n-t"><slot name="date" /><slot /></span>' },
      },
    },
    props: { bucket: value },
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
});
