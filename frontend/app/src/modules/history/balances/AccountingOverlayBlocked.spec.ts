import type { HistoricalBalanceStop } from '@/modules/history/balances/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import AccountingOverlayBlocked from '@/modules/history/balances/AccountingOverlayBlocked.vue';
import { IssueKind } from '@/modules/history/data-issues/constants';

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { required: true, type: Object } },
  template: '<a><slot /></a>',
});

const STOPPING_EVENT = 7;
const LATER_EVENT = 9;

function mountBlocked(stop: HistoricalBalanceStop, eventIdentifier: number = LATER_EVENT): VueWrapper {
  return mount(AccountingOverlayBlocked, {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
        RuiIcon: true,
        RuiTooltip: { template: '<div><slot name="activator" /><span data-testid="explanation"><slot /></span></div>' },
      },
    },
    props: { asset: 'ETH', eventIdentifier, stop },
  });
}

describe('accountingOverlayBlocked.vue', () => {
  describe('on a row after the stopping event', () => {
    it('should link to the data issue of the stop when it has one', () => {
      const wrapper = mountBlocked({ eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: 3 });
      expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
        name: '/history/data-issues/[[tab]]',
        params: { tab: 'issues' },
        query: { issue: '3' },
      });
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.open_issue');
    });

    it('should link to the stopping event with the overlay kept on when the stop has no data issue', () => {
      const wrapper = mountBlocked({ eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: null });
      expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
        name: '/history/events/',
        query: { asset: 'ETH', highlightedNegativeBalanceEvent: '7', overlay: 'balance', targetGroupIdentifier: 'group' },
      });
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.view_event');
    });

    it('should render no link when the stop has neither an issue nor a surviving event', () => {
      const wrapper = mountBlocked({ eventIdentifier: STOPPING_EVENT, groupIdentifier: null, issueId: null });
      expect(wrapper.findComponent({ name: 'RouterLink' }).exists()).toBe(false);
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.no_link');
    });
  });

  describe('on the stopping event row itself', () => {
    it('should link to the data issue and blame this event when the stop has an issue', () => {
      const wrapper = mountBlocked({ eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: 3 }, STOPPING_EVENT);
      expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
        name: '/history/data-issues/[[tab]]',
        params: { tab: 'issues' },
        query: { issue: '3' },
      });
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.self_open_issue');
    });

    it('should not link back to itself and blame this event when the stop has no issue', () => {
      const wrapper = mountBlocked({ eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: null }, STOPPING_EVENT);
      expect(wrapper.findComponent({ name: 'RouterLink' }).exists()).toBe(false);
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.self_no_link');
    });
  });

  describe('when the stop is a negative balance issue explicitly', () => {
    it.each([
      [
        'open_issue',
        { eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: 3, issueKind: IssueKind.NEGATIVE_BALANCE },
        LATER_EVENT,
        'accounting_overlay.blocked.open_issue',
      ],
      [
        'view_event',
        { eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: null, issueKind: IssueKind.NEGATIVE_BALANCE },
        LATER_EVENT,
        'accounting_overlay.blocked.view_event',
      ],
      [
        'no_link',
        { eventIdentifier: STOPPING_EVENT, groupIdentifier: null, issueId: null, issueKind: IssueKind.NEGATIVE_BALANCE },
        LATER_EVENT,
        'accounting_overlay.blocked.no_link',
      ],
      [
        'self_open_issue',
        { eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: 3, issueKind: IssueKind.NEGATIVE_BALANCE },
        STOPPING_EVENT,
        'accounting_overlay.blocked.self_open_issue',
      ],
      [
        'self_no_link',
        { eventIdentifier: STOPPING_EVENT, groupIdentifier: 'group', issueId: null, issueKind: IssueKind.NEGATIVE_BALANCE },
        STOPPING_EVENT,
        'accounting_overlay.blocked.self_no_link',
      ],
    ])('should use the negative balance explanation for %s', (_state, stop, eventIdentifier, expectedKey) => {
      const wrapper = mountBlocked(stop, eventIdentifier);
      expect(wrapper.get('[data-testid=explanation]').text()).toBe(expectedKey);
    });
  });

  describe('when the stop is an invalid event amount', () => {
    it('should link to the data issue and explain the negative event amount on a later row', () => {
      const wrapper = mountBlocked({
        eventIdentifier: STOPPING_EVENT,
        groupIdentifier: 'group',
        issueId: 3,
        issueKind: IssueKind.INVALID_EVENT_AMOUNT,
      });
      expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
        name: '/history/data-issues/[[tab]]',
        params: { tab: 'issues' },
        query: { issue: '3' },
      });
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.invalid_event_amount.open_issue');
    });

    it('should link to the stopping event and explain the negative event amount when there is no issue', () => {
      const wrapper = mountBlocked({
        eventIdentifier: STOPPING_EVENT,
        groupIdentifier: 'group',
        issueId: null,
        issueKind: IssueKind.INVALID_EVENT_AMOUNT,
      });
      expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
        name: '/history/events/',
        query: { asset: 'ETH', highlightedNegativeBalanceEvent: '7', overlay: 'balance', targetGroupIdentifier: 'group' },
      });
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.invalid_event_amount.view_event');
    });

    it('should render no link and explain the negative event amount when neither issue nor event exists', () => {
      const wrapper = mountBlocked({
        eventIdentifier: STOPPING_EVENT,
        groupIdentifier: null,
        issueId: null,
        issueKind: IssueKind.INVALID_EVENT_AMOUNT,
      });
      expect(wrapper.findComponent({ name: 'RouterLink' }).exists()).toBe(false);
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.invalid_event_amount.no_link');
    });

    it('should link to the data issue and blame this event for a negative amount on its own row', () => {
      const wrapper = mountBlocked({
        eventIdentifier: STOPPING_EVENT,
        groupIdentifier: 'group',
        issueId: 3,
        issueKind: IssueKind.INVALID_EVENT_AMOUNT,
      }, STOPPING_EVENT);
      expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
        name: '/history/data-issues/[[tab]]',
        params: { tab: 'issues' },
        query: { issue: '3' },
      });
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.invalid_event_amount.self_open_issue');
    });

    it('should not link back to itself and blame this event for a negative amount when there is no issue', () => {
      const wrapper = mountBlocked({
        eventIdentifier: STOPPING_EVENT,
        groupIdentifier: 'group',
        issueId: null,
        issueKind: IssueKind.INVALID_EVENT_AMOUNT,
      }, STOPPING_EVENT);
      expect(wrapper.findComponent({ name: 'RouterLink' }).exists()).toBe(false);
      expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.invalid_event_amount.self_no_link');
    });
  });
});
