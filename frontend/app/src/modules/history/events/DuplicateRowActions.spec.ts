import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DuplicateRowActions from './DuplicateRowActions.vue';

type Mode = 'auto-fix' | 'manual-review' | 'ignored';

function mountActions(mode: Mode, loading: { fix?: boolean; ignore?: boolean } = {}): VueWrapper<InstanceType<typeof DuplicateRowActions>> {
  return mount(DuplicateRowActions, {
    props: { fixLoading: loading.fix ?? false, ignoreLoading: loading.ignore ?? false, mode },
  });
}

describe('modules/history/events/DuplicateRowActions', () => {
  it('should offer both fix and ignore in auto-fix mode', async () => {
    const wrapper = mountActions('auto-fix');
    const buttons = wrapper.findAll('button');

    expect(buttons).toHaveLength(2);

    await buttons[0].trigger('click');
    await buttons[1].trigger('click');

    expect(wrapper.emitted('fix')).toHaveLength(1);
    expect(wrapper.emitted('ignore')).toHaveLength(1);
    expect(wrapper.emitted('restore')).toBeUndefined();
  });

  it('should offer only ignore in manual-review mode', async () => {
    const wrapper = mountActions('manual-review');
    const buttons = wrapper.findAll('button');

    expect(buttons).toHaveLength(1);

    await buttons[0].trigger('click');

    expect(wrapper.emitted('ignore')).toHaveLength(1);
    expect(wrapper.emitted('fix')).toBeUndefined();
    expect(wrapper.emitted('restore')).toBeUndefined();
  });

  it('should offer only restore in ignored mode', async () => {
    const wrapper = mountActions('ignored');
    const buttons = wrapper.findAll('button');

    expect(buttons).toHaveLength(1);

    await buttons[0].trigger('click');

    expect(wrapper.emitted('restore')).toHaveLength(1);
    expect(wrapper.emitted('ignore')).toBeUndefined();
    expect(wrapper.emitted('fix')).toBeUndefined();
  });

  it('should never render the fix action outside auto-fix mode', () => {
    expect(mountActions('manual-review').text()).not.toContain('fix');
    expect(mountActions('ignored').text()).not.toContain('fix');
  });
});
