import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent, h } from 'vue';
import ConfirmInPlace from './ConfirmInPlace.vue';

/** A plain button for an activator, so the spec owns what `ask` is bound to. */
const Activator = defineComponent({
  props: { ask: { required: true, type: Function } },
  setup(props) {
    return (): ReturnType<typeof h> => h('button', { 'data-testid': 'trigger', 'onClick': () => props.ask() }, 'Delete');
  },
});

function createWrapper(): VueWrapper<InstanceType<typeof ConfirmInPlace>> {
  return mount(ConfirmInPlace, {
    attachTo: document.body,
    attrs: { 'class': 'grow', 'data-testid': 'delete-confirm' },
    props: { question: { confirmLabel: 'Delete', message: 'Delete this key?', tone: 'error' } },
    slots: { activator: ({ ask }: { ask: () => void }) => h(Activator, { ask }) },
  });
}

async function ask(wrapper: VueWrapper): Promise<void> {
  await wrapper.find('[data-testid=trigger]').trigger('click');
}

describe('confirmInPlace', () => {
  it('should show the question in place of the trigger, without confirming, when asked', async () => {
    const wrapper = createWrapper();

    await ask(wrapper);

    const question = wrapper.find('[data-testid=delete-confirm]');
    expect(question.classes()).toContain('grow');
    expect(question.find('[data-testid=inline-confirm]').text()).toContain('Delete this key?');
    expect(wrapper.find('[data-testid=trigger]').exists()).toBe(false);
    expect(wrapper.emitted('confirm')).toBeUndefined();
  });

  it('should emit confirm once on accept and bring the trigger back focused', async () => {
    const wrapper = createWrapper();

    await ask(wrapper);
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(wrapper.emitted('confirm')).toHaveLength(1);
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.find('[data-testid=trigger]').element);
  });

  it('should bring the trigger back focused on cancel, without confirming', async () => {
    const wrapper = createWrapper();

    await ask(wrapper);
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

    expect(wrapper.emitted('confirm')).toBeUndefined();
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(document.activeElement).toBe(wrapper.find('[data-testid=trigger]').element);
  });

  it('should cancel on escape, without confirming', async () => {
    const wrapper = createWrapper();

    await ask(wrapper);
    await wrapper.find('[data-testid=inline-confirm]').trigger('keydown', { key: 'Escape' });

    expect(wrapper.emitted('confirm')).toBeUndefined();
    expect(document.activeElement).toBe(wrapper.find('[data-testid=trigger]').element);
  });
});
