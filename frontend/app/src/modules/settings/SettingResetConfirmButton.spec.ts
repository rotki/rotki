import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import SettingResetConfirmButton from './SettingResetConfirmButton.vue';

vi.mock('@/services/websocket/websocket-service');

const menuModel = ref<boolean>(false);

const RuiMenuStub = defineComponent({
  props: { modelValue: { type: Boolean, default: false } },
  emits: ['update:modelValue'],
  setup(props, { emit }) {
    watch(() => props.modelValue, val => set(menuModel, val));
    watch(menuModel, val => emit('update:modelValue', val));
    return { menuModel };
  },
  template: `
    <div data-testid="menu">
      <div data-testid="menu-activator"><slot name="activator" :attrs="{}" /></div>
      <div v-if="modelValue" data-testid="menu-content"><slot /></div>
    </div>
  `,
});

describe('modules/settings/SettingResetConfirmButton', () => {
  let wrapper: VueWrapper<InstanceType<typeof SettingResetConfirmButton>>;
  let pinia: Pinia;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof SettingResetConfirmButton>> {
    set(menuModel, false);
    return mount(SettingResetConfirmButton, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiButton: {
            template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
            inheritAttrs: false,
          },
          RuiIcon: {
            template: '<span data-testid="icon">{{ name }}</span>',
            props: ['name'],
          },
          RuiMenu: RuiMenuStub,
          RuiTooltip: {
            template: '<div data-testid="tooltip"><slot name="activator" /><span data-testid="tooltip-text"><slot /></span></div>',
          },
        },
      },
      props,
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should render the reset button with history icon', () => {
    wrapper = createWrapper();
    const icon = wrapper.find('[data-testid="icon"]');
    expect(icon.exists()).toBe(true);
    expect(icon.text()).toBe('lu-history');
  });

  it('should show tooltip text as i18n key', () => {
    wrapper = createWrapper();
    const tooltipText = wrapper.find('[data-testid="tooltip-text"]');
    expect(tooltipText.text()).toBe('settings.reset_confirm.tooltip');
  });

  it('should show custom tooltip when provided', () => {
    wrapper = createWrapper({ tooltip: 'Custom tooltip' });
    const tooltipText = wrapper.find('[data-testid="tooltip-text"]');
    expect(tooltipText.text()).toBe('Custom tooltip');
  });

  it('should apply compact classes when compact is true', () => {
    wrapper = createWrapper({ compact: true });
    const button = wrapper.find('[data-testid="menu-activator"] button');
    expect(button.classes()).toContain('ml-1');
    expect(button.classes()).not.toContain('mt-1');
  });

  it('should apply default classes when compact is false', () => {
    wrapper = createWrapper();
    const button = wrapper.find('[data-testid="menu-activator"] button');
    expect(button.classes()).toContain('mt-1');
    expect(button.classes()).toContain('ml-2');
  });

  it('should not show menu content initially', () => {
    wrapper = createWrapper();
    expect(wrapper.find('[data-testid="menu-content"]').exists()).toBe(false);
  });

  it('should disable the button when disabled prop is true', () => {
    wrapper = createWrapper({ disabled: true });
    const button = wrapper.find('[data-testid="menu-activator"] button');
    expect(button.attributes('disabled')).toBeDefined();
  });

  describe('when menu is open', () => {
    async function openMenu(): Promise<void> {
      set(menuModel, true);
      await wrapper.vm.$nextTick();
    }

    it('should show confirmation message and action buttons', async () => {
      wrapper = createWrapper();
      await openMenu();

      const content = wrapper.find('[data-testid="menu-content"]');
      expect(content.exists()).toBe(true);
      expect(content.text()).toContain('settings.reset_confirm.message');
      expect(content.text()).toContain('settings.reset_confirm.cancel');
      expect(content.text()).toContain('settings.reset_confirm.confirm');
    });

    it('should emit confirm when confirm button is clicked', async () => {
      wrapper = createWrapper();
      await openMenu();

      const buttons = wrapper.findAll('[data-testid="menu-content"] button');
      const confirmButton = buttons.find(btn => btn.text() === 'settings.reset_confirm.confirm');
      expect(confirmButton).toBeDefined();
      await confirmButton!.trigger('click');

      expect(wrapper.emitted('confirm')).toBeDefined();
    });

    it('should not emit confirm when cancel button is clicked', async () => {
      wrapper = createWrapper();
      await openMenu();

      const buttons = wrapper.findAll('[data-testid="menu-content"] button');
      const cancelButton = buttons.find(btn => btn.text() === 'settings.reset_confirm.cancel');
      expect(cancelButton).toBeDefined();
      await cancelButton!.trigger('click');

      expect(wrapper.emitted('confirm')).toBeUndefined();
    });
  });
});
