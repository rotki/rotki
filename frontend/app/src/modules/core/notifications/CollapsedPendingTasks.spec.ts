import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import CollapsedPendingTasks from '@/modules/core/notifications/CollapsedPendingTasks.vue';

function createWrapper(props: Partial<InstanceType<typeof CollapsedPendingTasks>['$props']> = {}): VueWrapper {
  return mount(CollapsedPendingTasks, {
    props: {
      count: 1,
      modelValue: true,
      percentage: 36,
      steps: { current: 4, total: 11 },
      ...props,
    },
  });
}

describe('collapsedPendingTasks', () => {
  it('should count jobs, not the activities they fan out into', () => {
    expect(createWrapper({ count: 1 }).text()).toContain('collapsed_pending_tasks.title::1');
  });

  it('should show the tally and a determinate ring when the work is quantifiable', () => {
    const wrapper = createWrapper();

    expect(wrapper.text()).toContain('collapsed_pending_tasks.steps::4, 11');
    expect(wrapper.findComponent({ name: 'RuiProgress' }).props('variant')).toBe('determinate');
  });

  it('should fall back to an indeterminate ring with no tally', () => {
    const wrapper = createWrapper({ percentage: -1, steps: { current: 0, total: 0 } });

    expect(wrapper.text()).not.toContain('collapsed_pending_tasks.steps');
    expect(wrapper.findComponent({ name: 'RuiProgress' }).props('variant')).toBe('indeterminate');
  });

  it('should toggle the panel', async () => {
    const wrapper = createWrapper({ modelValue: true });
    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
  });
});
