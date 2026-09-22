import type { JobBreakdownEntry } from '@/modules/task-center/use-job-breakdown';
import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { activityOutcome } from '@/modules/task-center/activity-outcome';
import DockJobBreakdown from '@/modules/task-center/components/DockJobBreakdown.vue';
import { ActivityStatus } from '@/modules/task-center/core/types';

/** `RuiIcon` is stubbed globally to render its name, so the mark's text is the icon it shows. */
function markOf(entry: Omit<JobBreakdownEntry, 'key' | 'label'>): { icon: string; classes: string[]; label: string | undefined } {
  const wrapper = mount(DockJobBreakdown, { props: { entries: [{ key: 'sync', label: 'Transaction sync', ...entry }] } });
  const mark = wrapper.find('[data-testid=dock-job-breakdown-mark]');
  return { classes: mark.classes(), icon: mark.text(), label: mark.attributes('aria-label') };
}

describe('dockJobBreakdown', () => {
  it('should mark a cancelled section the way a cancelled row is marked, not as a warning', () => {
    const mark = markOf({ problem: ActivityStatus.CANCELLED, settled: 7, total: 7 });

    expect(mark.icon).toBe(activityOutcome(ActivityStatus.CANCELLED).icon);
    expect(mark.classes).toContain('text-rui-text-secondary');
    expect(mark.classes).not.toContain('text-rui-warning');
    expect(mark.label).toBe('pending_task.status.cancelled');
  });

  it('should let a failure outrank a fully counted section', () => {
    const mark = markOf({ problem: ActivityStatus.FAILED, settled: 7, total: 7 });

    expect(mark.icon).toBe(activityOutcome(ActivityStatus.FAILED).icon);
    expect(mark.classes).toContain('text-rui-error');
  });

  it('should mark a fully counted section done, and one still counting as running', () => {
    expect(markOf({ settled: 7, total: 7 }).icon).toBe(activityOutcome(ActivityStatus.COMPLETE).icon);

    const counting = markOf({ settled: 3, total: 7 });
    expect(counting.icon).toBe(activityOutcome(ActivityStatus.PENDING).icon);
    expect(counting.label).toBe('pending_task.status.running');
  });
});
