import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import BigDialog from './BigDialog.vue';

describe('modules/shell/components/dialogs/BigDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof BigDialog>>;
  let pinia: Pinia;

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof BigDialog>> {
    return mount(BigDialog, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiBottomSheet: {
            template: '<div data-testid="bottom-sheet"><slot /></div>',
          },
          RuiButton: {
            inheritAttrs: false,
            template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>',
          },
          RuiCard: {
            template: '<div><slot name="custom-header" /><slot /><slot name="footer" /></div>',
          },
          RuiChip: {
            template: '<span><slot /></span>',
          },
          RuiDivider: {
            template: '<hr />',
          },
          RuiTooltip: {
            template: '<div><slot name="activator" /><slot /></div>',
          },
        },
      },
      props: {
        display: true,
        primaryAction: 'Save',
        title: 'Test dialog',
        ...props,
      },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should emit confirm when the form is submitted and not loading', async () => {
    wrapper = createWrapper({ loading: false });

    await wrapper.find('form').trigger('submit');

    expect(wrapper.emitted('confirm')).toHaveLength(1);
  });

  it('should not emit confirm again while a submit is in flight', async () => {
    wrapper = createWrapper({ loading: true });

    await wrapper.find('form').trigger('submit');
    await wrapper.find('form').trigger('submit');

    expect(wrapper.emitted('confirm')).toBeUndefined();
  });

  it('should disable the confirm button while loading', () => {
    wrapper = createWrapper({ loading: true });

    const confirmButton = wrapper.find('[data-cy="confirm"]');
    expect(confirmButton.exists()).toBe(true);
    expect(confirmButton.attributes('disabled')).toBeDefined();
  });
});
