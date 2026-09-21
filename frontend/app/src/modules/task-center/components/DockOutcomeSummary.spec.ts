import type { StatusTally } from '@/modules/task-center/core/status';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DockOutcomeSummary from '@/modules/task-center/components/DockOutcomeSummary.vue';
import { ActivityStatus } from '@/modules/task-center/core/types';

function createWrapper(counts: Partial<StatusTally>): VueWrapper {
  const tally: StatusTally = {
    [ActivityStatus.CANCELLED]: 0,
    [ActivityStatus.COMPLETE]: 0,
    [ActivityStatus.FAILED]: 0,
    [ActivityStatus.PENDING]: 0,
    [ActivityStatus.RUNNING]: 0,
    [ActivityStatus.SKIPPED]: 0,
    ...counts,
  };
  return mount(DockOutcomeSummary, { props: { tally } });
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
});
