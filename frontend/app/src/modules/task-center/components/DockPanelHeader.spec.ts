import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DockPanelHeader from '@/modules/task-center/components/DockPanelHeader.vue';
import { tallyStatuses } from '@/modules/task-center/core/status';
import { ActivityStatus } from '@/modules/task-center/core/types';

function createWrapper(statuses: ActivityStatus[], summary = true): VueWrapper {
  return mount(DockPanelHeader, {
    props: {
      summary,
      tally: tallyStatuses(statuses),
      title: 'Finished with problems',
      total: statuses.length,
    },
  });
}

describe('dockPanelHeader', () => {
  it('should show its title', () => {
    expect(createWrapper([ActivityStatus.COMPLETE]).text()).toContain('Finished with problems');
  });

  it('should count every settled leaf as finished, whatever it settled as, and nothing still in flight', () => {
    const wrapper = createWrapper([
      ActivityStatus.COMPLETE,
      ActivityStatus.FAILED,
      ActivityStatus.SKIPPED,
      ActivityStatus.CANCELLED,
      ActivityStatus.RUNNING,
      ActivityStatus.PENDING,
    ]);

    expect(wrapper.find('[data-testid=dock-panel-settled]').text()).toBe('task_dock.panel.settled::4, 6');
    expect(wrapper.find('[role=progressbar]').attributes('aria-valuenow')).toBe('4');
  });

  it('should name failures beside the count, in the error colour, over what is still running', () => {
    const detail = createWrapper([ActivityStatus.FAILED, ActivityStatus.RUNNING]).find('[data-testid=dock-panel-detail]');

    expect(detail.text()).toBe('task_dock.panel.detail.failed::1');
    expect(detail.classes()).toContain('text-rui-error');
  });

  it('should name what is running beside the count while nothing failed', () => {
    const detail = createWrapper([ActivityStatus.COMPLETE, ActivityStatus.RUNNING, ActivityStatus.RUNNING]).find('[data-testid=dock-panel-detail]');

    expect(detail.text()).toBe('task_dock.panel.detail.running::2');
    expect(detail.classes()).not.toContain('text-rui-error');
  });

  it('should split the bar by outcome, sized by share of all leaves, leaving out outcomes nobody had', () => {
    const wrapper = createWrapper([ActivityStatus.COMPLETE, ActivityStatus.COMPLETE, ActivityStatus.FAILED, ActivityStatus.RUNNING]);

    expect(wrapper.find('[data-testid=dock-panel-bar-complete]').attributes('style')).toContain('width: 50%');
    expect(wrapper.find('[data-testid=dock-panel-bar-failed]').attributes('style')).toContain('width: 25%');
    expect(wrapper.find('[data-testid=dock-panel-bar-skipped]').exists()).toBe(false);
  });

  it('should leave out the bar and count when it is not summarising, as for a single job', () => {
    const wrapper = createWrapper([ActivityStatus.COMPLETE, ActivityStatus.RUNNING], false);

    expect(wrapper.text()).toContain('Finished with problems');
    expect(wrapper.find('[role=progressbar]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=dock-panel-settled]').exists()).toBe(false);
  });

  it('should draw no bar and no count when there is nothing to count', () => {
    expect(createWrapper([]).find('[role=progressbar]').exists()).toBe(false);
  });

  it('should ask to collapse the panel', async () => {
    const wrapper = createWrapper([ActivityStatus.COMPLETE]);

    await wrapper.find('[aria-label="pending_task.collapse"]').trigger('click');

    expect(wrapper.emitted('collapse')).toHaveLength(1);
  });
});
