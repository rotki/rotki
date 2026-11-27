import type { HistoryEventsRestrictions } from '@/modules/history/events/history-events-restrictions';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import AccountHistoryEvents from '@/modules/balances/account-history/components/AccountHistoryEvents.vue';

function createWrapper(props: InstanceType<typeof AccountHistoryEvents>['$props']): VueWrapper<InstanceType<typeof AccountHistoryEvents>> {
  return mount(AccountHistoryEvents, {
    global: {
      stubs: { HistoryEventsView: { name: 'HistoryEventsView', props: ['restrictions', 'sectionTitle'], template: '<div />' } },
    },
    props,
  });
}

function restrictionsOf(wrapper: VueWrapper<InstanceType<typeof AccountHistoryEvents>>): HistoryEventsRestrictions {
  return wrapper.findComponent({ name: 'HistoryEventsView' }).props('restrictions');
}

describe('account history events', () => {
  it('should pin the events list to the account, asset, location and range', () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH', location: 'optimism', range: { from: 100, to: 200 } });

    expect(restrictionsOf(wrapper)).toEqual({
      asset: 'ETH',
      externalAccounts: [{ address: '0xA', chain: 'optimism' }],
      location: 'optimism',
      period: { fromTimestamp: 100, toTimestamp: 200 },
    });
  });

  it('should leave the location and period open for every location and all time', () => {
    const wrapper = createWrapper({ account: '0xA', asset: 'ETH', range: { from: 0, to: 200 } });
    const restrictions = restrictionsOf(wrapper);

    expect(restrictions.location).toBeUndefined();
    expect(restrictions.period).toBeUndefined();
    expect(restrictions.externalAccounts?.map(({ address }) => address)).toEqual(['0xA']);
  });
});
