import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { defineComponent, h, nextTick, type Ref, ref } from 'vue';
import ConfirmMenu from '@/modules/shell/components/ConfirmMenu.vue';
import { useConfirmMenuAsk } from '@/modules/shell/components/use-confirm-menu';

const QUESTION: ConfirmQuestion = { confirmLabel: 'Delete', message: 'Delete the report?', title: 'Delete report', tone: 'error' };

/** Renders its content only while open, and closes on a content click it sees, as `RuiMenu` does. */
const RuiMenu = defineComponent({
  emits: ['update:modelValue'],
  name: 'RuiMenu',
  props: {
    classNames: { default: undefined, type: Object },
    closeOnContentClick: Boolean,
    modelValue: Boolean,
    role: { default: 'menu', type: String },
  },
  template: `<div>
    <slot name="activator" :attrs="{}" />
    <div v-if="modelValue" data-testid="menu-content" :role="role" @click="closeOnContentClick && $emit('update:modelValue', false)">
      <slot />
    </div>
  </div>`,
});

/** An entry that is a component of its own, so it asks through the injection, not the slot. */
const AskingEntry = defineComponent({
  emits: ['accepted'],
  setup(_props, { emit }) {
    const ask = useConfirmMenuAsk();
    return (): ReturnType<typeof h> => h('button', {
      'data-testid': 'component-entry',
      'onClick': () => ask?.(QUESTION, () => emit('accepted')),
    }, 'Delete');
  },
});

interface Mounted {
  wrapper: VueWrapper;
  open: Ref<boolean>;
}

function createWrapper(onAccept: () => void): Mounted {
  const open = ref<boolean>(true);
  const wrapper = mount({
    components: { AskingEntry, ConfirmMenu },
    setup: () => ({ onAccept, open, question: QUESTION }),
    template: `
      <ConfirmMenu v-model="open" menu-class="max-w-60" close-on-content-click>
        <template #activator="{ attrs }"><button v-bind="attrs">More</button></template>
        <template #default="{ ask }">
          <button data-testid="other-entry">Export</button>
          <button data-testid="inline-entry" @click="ask(question, onAccept)">Delete</button>
          <AskingEntry @accepted="onAccept()" />
        </template>
      </ConfirmMenu>`,
  }, { attachTo: document.body, global: { provide: libraryDefaults, stubs: { RuiMenu } } });
  return { open, wrapper };
}

function entriesHidden(wrapper: VueWrapper): boolean {
  return (wrapper.find('[data-testid=confirm-menu-entries]').attributes('style') ?? '').includes('display: none');
}

describe('modules/shell/components/ConfirmMenu', () => {
  it('should keep the menu open through the asking click, as a dialog showing the question in place of the hidden entries', async () => {
    const onAccept = vi.fn<() => void>();
    const { open, wrapper } = createWrapper(onAccept);

    await wrapper.find('[data-testid=inline-entry]').trigger('click');

    expect(get(open)).toBe(true);
    expect(wrapper.find('[data-testid=menu-content]').attributes('role')).toBe('dialog');
    expect(wrapper.findComponent(RuiMenu).props('classNames')).toEqual({ menu: 'w-72' });
    expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('Delete the report?');
    expect(entriesHidden(wrapper)).toBe(true);
    expect(document.activeElement).toBe(wrapper.find('[data-testid=inline-confirm-cancel]').element);
    expect(onAccept).not.toHaveBeenCalled();
  });

  it('should still close on a click on an entry that does not ask', async () => {
    const { open, wrapper } = createWrapper(vi.fn<() => void>());

    await wrapper.find('[data-testid=other-entry]').trigger('click');

    expect(get(open)).toBe(false);
  });

  it('should close the menu, then run the callback while the asking entry is still mounted, once accepted', async () => {
    const seen: { open: boolean; mounted: boolean }[] = [];
    const { open, wrapper } = createWrapper(() => {
      seen.push({ mounted: wrapper.find('[data-testid=component-entry]').exists(), open: get(open) });
    });

    await wrapper.find('[data-testid=component-entry]').trigger('click');
    await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

    expect(seen).toEqual([{ mounted: true, open: false }]);
  });

  it('should bring the entries back on cancel, with focus on the entry that asked, without running the callback', async () => {
    const onAccept = vi.fn<() => void>();
    const { open, wrapper } = createWrapper(onAccept);
    const asker = wrapper.find<HTMLButtonElement>('[data-testid=inline-entry]');
    asker.element.focus();

    await asker.trigger('click');
    await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');
    await nextTick();

    expect(get(open)).toBe(true);
    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(entriesHidden(wrapper)).toBe(false);
    expect(wrapper.findComponent(RuiMenu).props('classNames')).toEqual({ menu: 'max-w-60' });
    expect(document.activeElement).toBe(asker.element);
    expect(onAccept).not.toHaveBeenCalled();
  });

  it('should drop the question when the menu closes, offering the entries on the next open', async () => {
    const onAccept = vi.fn<() => void>();
    const { open, wrapper } = createWrapper(onAccept);

    await wrapper.find('[data-testid=inline-entry]').trigger('click');
    set(open, false);
    await nextTick();
    set(open, true);
    await nextTick();

    expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
    expect(entriesHidden(wrapper)).toBe(false);
    expect(onAccept).not.toHaveBeenCalled();
  });
});
