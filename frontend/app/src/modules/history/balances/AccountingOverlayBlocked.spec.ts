import type { HistoricalBalanceStop } from '@/modules/history/balances/types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent } from 'vue';
import AccountingOverlayBlocked from '@/modules/history/balances/AccountingOverlayBlocked.vue';

const RouterLinkStub = defineComponent({
  name: 'RouterLink',
  props: { to: { required: true, type: Object } },
  template: '<a><slot /></a>',
});

function mountBlocked(stop: HistoricalBalanceStop): VueWrapper {
  return mount(AccountingOverlayBlocked, {
    global: {
      stubs: {
        RouterLink: RouterLinkStub,
        RuiIcon: true,
        RuiTooltip: { template: '<div><slot name="activator" /><span data-testid="explanation"><slot /></span></div>' },
      },
    },
    props: { asset: 'ETH', stop },
  });
}

describe('accountingOverlayBlocked.vue', () => {
  it('should link to the data issue of the stop when it has one', () => {
    const wrapper = mountBlocked({ eventIdentifier: 7, groupIdentifier: 'group', issueId: 3 });
    expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
      name: '/history/data-issues/[[tab]]',
      params: { tab: 'issues' },
      query: { issue: '3' },
    });
    expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.open_issue');
  });

  it('should link to the stopping event when the stop has no data issue', () => {
    const wrapper = mountBlocked({ eventIdentifier: 7, groupIdentifier: 'group', issueId: null });
    expect(wrapper.findComponent({ name: 'RouterLink' }).props('to')).toEqual({
      name: '/history/events/',
      query: { asset: 'ETH', highlightedNegativeBalanceEvent: '7', targetGroupIdentifier: 'group' },
    });
    expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.view_event');
  });

  it('should render no link when the stop has neither an issue nor a surviving event', () => {
    const wrapper = mountBlocked({ eventIdentifier: 7, groupIdentifier: null, issueId: null });
    expect(wrapper.findComponent({ name: 'RouterLink' }).exists()).toBe(false);
    expect(wrapper.get('[data-testid=explanation]').text()).toBe('accounting_overlay.blocked.no_link');
  });
});
