import type { StatusTally } from '@/modules/task-center/core/status';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DockOutcomeSummary from '@/modules/task-center/components/DockOutcomeSummary.vue';
import { ActivityStatus } from '@/modules/task-center/core/types';

function createWrapper(counts: Partial<StatusTally>, attention?: number): VueWrapper {
  const tally: StatusTally = {
    [ActivityStatus.CANCELLED]: 0,
    [ActivityStatus.COMPLETE]: 0,
    [ActivityStatus.FAILED]: 0,
    [ActivityStatus.PENDING]: 0,
    [ActivityStatus.RUNNING]: 0,
    [ActivityStatus.SKIPPED]: 0,
    ...counts,
  };
  return mount(DockOutcomeSummary, { props: { attention, tally } });
}

describe('dockOutcomeSummary', () => {
  it('should leave an expected skip or cancel in the secondary colour, and colour only a failure', () => {
    const wrapper = createWrapper({
      [ActivityStatus.CANCELLED]: 1,
      [ActivityStatus.COMPLETE]: 8,
      [ActivityStatus.FAILED]: 1,
      [ActivityStatus.SKIPPED]: 13,
    });

    expect(wrapper.find('[data-testid=dock-outcome-skipped]').classes()).toContain('text-rui-text-secondary');
    expect(wrapper.find('[data-testid=dock-outcome-cancelled]').classes()).toContain('text-rui-text-secondary');
    expect(wrapper.find('[data-testid=dock-outcome-failed]').classes()).toContain('text-rui-error');
  });

  it('should count the skips that asked for attention apart from the routine ones, in the warning colour', () => {
    const wrapper = createWrapper({ [ActivityStatus.SKIPPED]: 3 }, 1);

    expect(wrapper.find('[data-testid=dock-outcome-skipped]').text()).toBe('task_dock.panel.outcome.skipped::2');
    expect(wrapper.find('[data-testid=dock-outcome-attention]').text()).toBe('task_dock.panel.outcome.attention::1');
    expect(wrapper.find('[data-testid=dock-outcome-attention]').classes()).toContain('text-rui-warning');
  });

  it('should drop the skipped part when every skip asked for attention', () => {
    const wrapper = createWrapper({ [ActivityStatus.SKIPPED]: 2 }, 2);

    expect(wrapper.find('[data-testid=dock-outcome-skipped]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=dock-outcome-attention]').exists()).toBe(true);
  });
});
