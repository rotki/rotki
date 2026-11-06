import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import DuplicateRowActions from './DuplicateRowActions.vue';

type Mode = 'auto-fix' | 'manual-review' | 'ignored';

/** Opens through its activator and renders its content only while open, as the real menu does. */
const RuiMenu = {
  name: 'RuiMenu',
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: `<div>
    <slot name="activator" :attrs="{ onClick: () => $emit('update:modelValue', true) }" />
    <div v-if="modelValue"><slot /></div>
  </div>`,
};

function mountActions(mode: Mode, loading: { fix?: boolean; ignore?: boolean } = {}): VueWrapper<InstanceType<typeof DuplicateRowActions>> {
  return mount(DuplicateRowActions, {
    global: { stubs: { RuiMenu } },
    props: { fixLoading: loading.fix ?? false, ignoreLoading: loading.ignore ?? false, mode },
  });
}

async function accept(wrapper: VueWrapper, testId: string): Promise<void> {
  await wrapper.find(`[data-testid=${testId}]`).trigger('click');
  await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');
}

describe('modules/history/events/DuplicateRowActions', () => {
  it('should offer both fix and ignore in auto-fix mode', async () => {
    const wrapper = mountActions('auto-fix');

    await accept(wrapper, 'duplicate-row-fix');
    await accept(wrapper, 'duplicate-row-ignore');

    expect(wrapper.emitted('fix')).toHaveLength(1);
    expect(wrapper.emitted('ignore')).toHaveLength(1);
    expect(wrapper.emitted('restore')).toBeUndefined();
  });

  it('should offer only ignore in manual-review mode', async () => {
    const wrapper = mountActions('manual-review');

    expect(wrapper.find('[data-testid=duplicate-row-fix]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=duplicate-row-restore]').exists()).toBe(false);

    await accept(wrapper, 'duplicate-row-ignore');

    expect(wrapper.emitted('ignore')).toHaveLength(1);
  });

  it('should offer only restore in ignored mode', async () => {
    const wrapper = mountActions('ignored');

    expect(wrapper.find('[data-testid=duplicate-row-fix]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=duplicate-row-ignore]').exists()).toBe(false);

    await accept(wrapper, 'duplicate-row-restore');

    expect(wrapper.emitted('restore')).toHaveLength(1);
  });

  it('should ask what fixing the duplicate does before emitting', async () => {
    const wrapper = mountActions('auto-fix');

    await wrapper.find('[data-testid=duplicate-row-fix]').trigger('click');

    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('customized_event_duplicates.actions.fix_single_confirm');
    expect(wrapper.emitted('fix')).toBeUndefined();
  });

  it('should emit nothing when the question is cancelled', async () => {
    const wrapper = mountActions('ignored');

    await wrapper.find('[data-testid=duplicate-row-restore]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

    expect(wrapper.emitted('restore')).toBeUndefined();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
  });
});
