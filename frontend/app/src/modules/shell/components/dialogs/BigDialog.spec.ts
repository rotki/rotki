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
            template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /><slot name="append" /></button>',
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
        action: { primary: 'Save' },
        display: true,
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

    const confirmButton = wrapper.find('[data-testid="confirm"]');
    expect(confirmButton.exists()).toBe(true);
    expect(confirmButton.attributes('disabled')).toBeDefined();
  });

  it('should label both buttons from the action group', () => {
    wrapper = createWrapper({ action: { primary: 'Save', secondary: 'Discard' } });

    expect(wrapper.find('[data-testid="confirm"]').text()).toBe('Save');
    expect(wrapper.find('[data-testid="cancel"]').text()).toBe('Discard');
  });

  it('should fall back to the default labels when the action group omits them', () => {
    wrapper = createWrapper({ action: { primary: undefined, secondary: undefined } });

    expect(wrapper.find('[data-testid="confirm"]').text()).toBe('common.actions.confirm');
    expect(wrapper.find('[data-testid="cancel"]').text()).toBe('common.actions.cancel');
  });

  it('should disable the confirm button when the action group disables it', () => {
    wrapper = createWrapper({ action: { disabled: true, primary: 'Save' } });

    expect(wrapper.find('[data-testid="confirm"]').attributes('disabled')).toBeDefined();
  });

  it('should drop the confirm button when the action group hides it', () => {
    wrapper = createWrapper({ action: { hidden: true, primary: 'Save' } });

    expect(wrapper.find('[data-testid="confirm"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="cancel"]').exists()).toBe(true);
  });

  it('should badge the confirm button with the error count', () => {
    wrapper = createWrapper({ errors: { count: 3 } });

    const confirmButton = wrapper.find('[data-testid="confirm"]');
    expect(confirmButton.text()).toContain('3');
  });

  it('should not badge the confirm button when there are no errors', () => {
    wrapper = createWrapper({ errors: { count: 0 } });

    expect(wrapper.find('[data-testid="confirm"]').text()).toBe('Save');
  });

  it('should keep the minimum content height unless the layout group opts out', () => {
    wrapper = createWrapper();
    expect(wrapper.find('.min-h-\\[50vh\\]').exists()).toBe(true);

    wrapper.unmount();
    wrapper = createWrapper({ layout: { autoHeight: true } });
    expect(wrapper.find('.min-h-\\[50vh\\]').exists()).toBe(false);
  });
});
