import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import UnmatchedRowActions, {
  type UnmatchedRowActionLabels,
  type UnmatchedRowOptionalAction,
} from '@/modules/history/events/UnmatchedRowActions.vue';

const labels: UnmatchedRowActionLabels = {
  findMatch: 'Find match',
  ignore: 'Ignore',
  ignoreTooltip: 'Ignore tooltip',
  restore: 'Restore',
  restoreTooltip: 'Restore tooltip',
  showInEventsTooltip: 'Show in events',
};

const markExternal: UnmatchedRowOptionalAction = {
  label: 'Mark external',
  tooltip: 'Mark external tooltip',
};

interface Props {
  isPinned?: boolean;
  showRestore?: boolean;
  ignoreLoading?: boolean;
  matchDisabled?: boolean;
  markExternal?: UnmatchedRowOptionalAction;
  createCounterpart?: UnmatchedRowOptionalAction;
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

  it('should render the mark-external action only when one is given', async () => {
    const hidden = mountActions();
    expect(hidden.findAll('button').some(button => button.text() === 'Mark external')).toBe(false);

    const wrapper = mountActions({ markExternal });
    const button = wrapper.findAll('button').find(item => item.text() === 'Mark external');
    expect(button).toBeDefined();
    await button?.trigger('click');
    expect(wrapper.emitted('mark-external')).toHaveLength(1);
  });

  it('should render the create-counterpart action only when one is given', async () => {
    const hidden = mountActions();
    expect(hidden.findAll('button').some(button => button.text() === 'Create counterpart')).toBe(false);

    const wrapper = mountActions({
      createCounterpart: { label: 'Create counterpart', tooltip: 'Create counterpart tooltip' },
    });
    const button = wrapper.findAll('button').find(item => item.text() === 'Create counterpart');
    await button?.trigger('click');
    expect(wrapper.emitted('create-counterpart')).toHaveLength(1);
  });

  it('should fill an emphasized optional action and outline a plain one', () => {
    function variantOf(wrapper: VueWrapper, label: string): unknown {
      const button = wrapper
        .findAllComponents({ name: 'RuiButton' })
        .find(item => item.text() === label);
      return button?.props('variant');
    }

    expect(variantOf(mountActions({ markExternal }), 'Mark external')).toBe('outlined');
    expect(variantOf(
      mountActions({ markExternal: { ...markExternal, emphasize: true } }),
      'Mark external',
    )).toBe('default');
  });
});
