import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UpgradeRow from '@/modules/history/UpgradeRow.vue';

const PlanLimitMessageStub = {
  name: 'PlanLimitMessage',
  props: ['label', 'limit', 'total', 'range'],
  template: '<div class="plan-limit" />',
};

describe('upgradeRow', () => {
  function createWrapper(props: Record<string, unknown> = {}): VueWrapper {
    return mount(UpgradeRow, {
      props: { colspan: 5, label: 'events', limit: 10, total: 50, ...props },
      global: { stubs: { PlanLimitMessage: PlanLimitMessageStub } },
    });
  }

  it('should pass the counts, label and range on to the plan limit message', () => {
    const range = { timeEnd: 2000, timeStart: 1000 };
    const wrapper = createWrapper({ limit: 7, range, total: 42 });
    expect(wrapper.findComponent(PlanLimitMessageStub).props()).toEqual({ label: 'events', limit: 7, range, total: 42 });
  });

  it('should span the requested number of columns', () => {
    const wrapper = createWrapper({ colspan: 9 });
    expect(wrapper.find('td').attributes('colspan')).toBe('9');
  });
});
