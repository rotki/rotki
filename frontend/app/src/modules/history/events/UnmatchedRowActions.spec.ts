import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UnmatchedRowActions, { type UnmatchedRowActionLabels } from '@/modules/history/events/UnmatchedRowActions.vue';

const labels: UnmatchedRowActionLabels = {
  findMatch: 'Find match',
  ignore: 'Ignore',
  ignoreTooltip: 'Ignore tooltip',
  markExternal: 'Mark external',
  markExternalTooltip: 'Mark external tooltip',
  restore: 'Restore',
  restoreTooltip: 'Restore tooltip',
  showInEventsTooltip: 'Show in events',
};

interface Props {
  isPinned?: boolean;
  showRestore?: boolean;
  ignoreLoading?: boolean;
  matchDisabled?: boolean;
  showMarkExternal?: boolean;
}

function mountActions(props: Props = {}): VueWrapper<InstanceType<typeof UnmatchedRowActions>> {
  return mount(UnmatchedRowActions, {
    props: { labels, ...props },
  });
}

describe('modules/history/events/UnmatchedRowActions', () => {
  it('should render find-match and ignore actions by default', () => {
    const wrapper = mountActions();
    expect(wrapper.text()).toContain('Find match');
    expect(wrapper.text()).toContain('Ignore');
    expect(wrapper.text()).not.toContain('Restore');
    expect(wrapper.text()).not.toContain('Mark external');
  });

  it('should emit show-in-events when the first button is clicked', async () => {
    const wrapper = mountActions();
    await wrapper.findAll('button')[0].trigger('click');
    expect(wrapper.emitted('show-in-events')).toHaveLength(1);
  });

  it('should emit select when find-match is clicked', async () => {
    const wrapper = mountActions();
    const findMatch = wrapper.findAll('button').find(button => button.text() === 'Find match');
    await findMatch?.trigger('click');
    expect(wrapper.emitted('select')).toHaveLength(1);
  });

  it('should emit ignore when ignore is clicked', async () => {
    const wrapper = mountActions();
    const ignore = wrapper.findAll('button').find(button => button.text() === 'Ignore');
    await ignore?.trigger('click');
    expect(wrapper.emitted('ignore')).toHaveLength(1);
  });

  it('should disable find-match when matchDisabled is set', () => {
    const wrapper = mountActions({ matchDisabled: true });
    const findMatch = wrapper.findAll('button').find(button => button.text() === 'Find match');
    expect(findMatch?.attributes('disabled')).toBeDefined();
  });

  it('should show restore instead of match actions when showRestore is set', async () => {
    const wrapper = mountActions({ showRestore: true });
    expect(wrapper.text()).toContain('Restore');
    expect(wrapper.text()).not.toContain('Find match');
    const restore = wrapper.findAll('button').find(button => button.text() === 'Restore');
    await restore?.trigger('click');
    expect(wrapper.emitted('restore')).toHaveLength(1);
  });

  it('should render the mark-external action only when enabled', async () => {
    const hidden = mountActions();
    expect(hidden.findAll('button').some(button => button.text() === 'Mark external')).toBe(false);

    const wrapper = mountActions({ showMarkExternal: true });
    const markExternal = wrapper.findAll('button').find(button => button.text() === 'Mark external');
    expect(markExternal).toBeDefined();
    await markExternal?.trigger('click');
    expect(wrapper.emitted('mark-external')).toHaveLength(1);
  });
});
