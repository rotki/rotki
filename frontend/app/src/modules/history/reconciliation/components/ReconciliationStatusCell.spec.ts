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

  it('should link a stop whose event was deleted without a group or paging target', () => {
    const wrapper = mountCell(bucket({
      status: 'blocked',
      stop: {
        derivedBalanceBeforeEvent: bigNumberify('0.5'),
        eventIdentifier: 1234,
        eventTimestamp: 1_700_000_000_000,
        groupIdentifier: null,
        negativeAmount: bigNumberify('-1'),
      },
    }));

    expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
      name: '/history/events/',
      query: {
        asset: 'ETH',
        highlightedNegativeBalanceEvent: '1234',
      },
    });
  });

  it('should render the status icon as well as the label', () => {
    const wrapper = mountCell(bucket({ status: 'reconciled' }));

    expect(wrapper.text()).toContain('data_issues.reconciliation.status.matches');
    expect(wrapper.html()).toContain('lu-circle-check');
  });
});
