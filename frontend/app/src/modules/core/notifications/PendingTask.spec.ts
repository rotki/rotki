import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import PendingTask from '@/modules/core/notifications/PendingTask.vue';
import {
  type Activity,
  ActivityKind,
  ActivitySourceType,
  ActivityStatus,
  makeActivityId,
} from '@/modules/task-center/core/types';

const NOW = 1_000_000;

function activity(partial: Partial<Activity> = {}): Activity {
  return {
    cancellable: true,
    id: makeActivityId(ActivityKind.TX_SYNC, 'ethereum'),
    kind: ActivityKind.TX_SYNC,
    percentage: -1,
    rerunnable: false,
    source: { type: ActivitySourceType.NATIVE },
    status: ActivityStatus.RUNNING,
    title: 'Transaction sync',
    ...partial,
  };
}

function createWrapper(props: Partial<InstanceType<typeof PendingTask>['$props']> = {}): VueWrapper {
  return mount(PendingTask, {
    props: {
      activity: activity(),
      cancellable: false,
      now: NOW,
      percentage: -1,
      ...props,
    },
  });
}

describe('pendingTask', () => {
  it('should show the title and subtitle at the top level', () => {
    const text = createWrapper({ activity: activity({ subtitle: 'Ethereum' }) }).text();

    expect(text).toContain('Transaction sync');
    expect(text).toContain('Ethereum');
  });

  /**
   * A chain and its accounts carry the same title, so repeating it under a parent that already
   * names the job produced three identical-looking rows told apart only by their subtitle.
   */
  it('should show only its own identity when nested', () => {
    const text = createWrapper({
      activity: activity({ subtitle: 'Ethereum' }),
      nested: true,
    }).text();

    expect(text).toContain('Ethereum');
    expect(text).not.toContain('Transaction sync');
  });

  it('should render elapsed time for running work', () => {
    const text = createWrapper({ activity: activity({ startedAt: NOW - 14_000 }) }).text();

    expect(text).toContain('14s');
  });

  /** An absolute date on a live row answers a question nobody asked; a settled row has no elapsed at all. */
  it('should not render elapsed time once the work settled', () => {
    const text = createWrapper({
      activity: activity({ startedAt: NOW - 14_000, status: ActivityStatus.COMPLETE }),
    }).text();

    expect(text).not.toContain('14s');
  });

  it('should render its subtree tally next to the elapsed time', () => {
    const text = createWrapper({
      activity: activity({ startedAt: NOW - 5000 }),
      percentage: 25,
      steps: { current: 1, total: 4 },
    }).text();

    expect(text).toContain('pending_task.steps::1, 4');
  });

  it.each([
    [ActivityStatus.PENDING, 'pending_task.status.queued'],
    [ActivityStatus.FAILED, 'pending_task.status.failed'],
    [ActivityStatus.SKIPPED, 'pending_task.status.skipped'],
    [ActivityStatus.CANCELLED, 'pending_task.status.cancelled'],
    [ActivityStatus.COMPLETE, 'pending_task.status.done'],
  ])('should label a %s row with its outcome', (status, key) => {
    expect(createWrapper({ activity: activity({ status }) }).text()).toContain(key);
  });

  it('should show a spinner, not a chip, while running', () => {
    const wrapper = createWrapper({ activity: activity({ status: ActivityStatus.RUNNING }) });

    expect(wrapper.text()).not.toContain('pending_task.status');
    expect(wrapper.find('.animate-spin').exists()).toBe(true);
  });

  it('should emit cancel only when the caller allows it', async () => {
    const wrapper = createWrapper({ cancellable: true });
    await wrapper.find('button').trigger('click');

    expect(wrapper.emitted('cancel')).toHaveLength(1);
  });

  it('should render no cancel control when the caller withholds it', () => {
    expect(createWrapper({ cancellable: false }).find('button').exists()).toBe(false);
  });
});
