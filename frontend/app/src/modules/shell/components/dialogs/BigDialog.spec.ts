import { resetOverlayStack, useOverlayStack } from '@rotki/ui-library';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import BigDialog from './BigDialog.vue';

describe('modules/shell/components/dialogs/BigDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof BigDialog>>;
  let pinia: Pinia;

  /**
   * Mounts the dialog with its sheet stubbed as a pass-through.
   *
   * @remarks
   * `realSheet` mounts the library's bottom sheet instead, for tests that need its `RuiDialog`
   * registered on the overlay stack.
   */
  function createWrapper(
    props: Record<string, unknown> = {},
    slots: Record<string, string> = {},
    { realSheet = false }: { realSheet?: boolean } = {},
  ): VueWrapper<InstanceType<typeof BigDialog>> {
    return mount(BigDialog, {
      attachTo: document.body,
      global: {
        plugins: [pinia],
        stubs: {
          RuiBottomSheet: realSheet
            ? false
            : { template: '<div data-testid="bottom-sheet"><slot /></div>' },
          RuiButton: {
            emits: ['click'],
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
      slots,
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    resetOverlayStack();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should hand the save to its owner when the form is submitted and not loading', async () => {
    const onConfirm = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    wrapper = createWrapper({ loading: false, onConfirm });

    await wrapper.find('form').trigger('submit');

    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('should not hand the save over while the owner reports one in flight', async () => {
    const onConfirm = vi.fn<() => Promise<void>>().mockResolvedValue(undefined);
    wrapper = createWrapper({ loading: true, onConfirm });

    await wrapper.find('form').trigger('submit');

    expect(onConfirm).not.toHaveBeenCalled();
  });

  describe('while the save it handed over is still running', () => {
    function pendingSave(): { finish: () => void; onConfirm: () => Promise<void> } {
      let finish = (): void => {};
      const promise = new Promise<void>((resolve) => {
        finish = resolve;
      });
      return { finish: (): void => finish(), onConfirm: vi.fn<() => Promise<void>>(async () => promise) };
    }

    it('should not hand it over a second time', async () => {
      const { finish, onConfirm } = pendingSave();
      wrapper = createWrapper({ onConfirm });

      await wrapper.find('form').trigger('submit');
      await wrapper.find('form').trigger('submit');
      finish();
      await flushPromises();

      expect(onConfirm).toHaveBeenCalledOnce();
    });

    it('should disable the confirm button until it settles', async () => {
      const { finish, onConfirm } = pendingSave();
      wrapper = createWrapper({ onConfirm });

      await wrapper.find('form').trigger('submit');
      expect(wrapper.find('[data-testid="confirm"]').attributes('disabled')).toBeDefined();

      finish();
      await flushPromises();
      expect(wrapper.find('[data-testid="confirm"]').attributes('disabled')).toBeUndefined();
    });

    it('should start a reopened dialog with the confirm button enabled', async () => {
      const { finish, onConfirm } = pendingSave();
      wrapper = createWrapper({ onConfirm });

      await wrapper.find('form').trigger('submit');
      await wrapper.setProps({ display: false });
      await wrapper.setProps({ display: true });

      expect(wrapper.find('[data-testid="confirm"]').attributes('disabled')).toBeUndefined();
      finish();
      await flushPromises();
    });

    it('should keep a save started after reopening in flight when the earlier one settles', async () => {
      const first = pendingSave();
      const second = pendingSave();
      wrapper = createWrapper({ onConfirm: first.onConfirm });

      await wrapper.find('form').trigger('submit');
      await wrapper.setProps({ display: false });
      await wrapper.setProps({ display: true, onConfirm: second.onConfirm });
      await wrapper.find('form').trigger('submit');
      first.finish();
      await flushPromises();

      expect(wrapper.find('[data-testid="confirm"]').attributes('disabled')).toBeDefined();
      second.finish();
      await flushPromises();
    });

    it('should focus a field the save marked invalid once it settles', async () => {
      const { finish, onConfirm } = pendingSave();
      wrapper = createWrapper({ onConfirm }, { default: '<input data-testid="rejected" />' });
      const rejected = wrapper.find('[data-testid="rejected"]').element;

      await wrapper.find('form').trigger('submit');
      await flushPromises();
      rejected.setAttribute('aria-invalid', 'true');
      finish();
      await flushPromises();

      expect(document.activeElement).toBe(rejected);
    });
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

  it('should focus the first invalid field on confirm, without being told an error count', async () => {
    wrapper = createWrapper({}, {
      default: '<input data-testid="valid" /><input data-testid="invalid" aria-invalid="true" />',
    });

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(document.activeElement).toBe(wrapper.find('[data-testid="invalid"]').element);
  });

  it('should leave focus alone on confirm when every field is valid', async () => {
    wrapper = createWrapper({}, { default: '<input data-testid="valid" aria-invalid="false" />' });

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(document.activeElement).not.toBe(wrapper.find('[data-testid="valid"]').element);
  });

  it('should not reach into the page behind it once its content is gone', async () => {
    document.body.insertAdjacentHTML('beforeend', '<input id="behind" aria-invalid="true" />');
    wrapper = createWrapper({ display: false }, { default: '<input aria-invalid="true" />' });

    await wrapper.find('form').trigger('submit');
    await flushPromises();

    expect(document.activeElement).not.toBe(document.querySelector('#behind'));
  });

  it('should focus the first invalid field when the error count rises after the save', async () => {
    wrapper = createWrapper(
      { errors: { autoFocus: true, count: 0 } },
      { default: '<input data-testid="invalid" aria-invalid="true" />' },
    );

    await wrapper.setProps({ errors: { autoFocus: true, count: 1 } });
    await flushPromises();

    expect(document.activeElement).toBe(wrapper.find('[data-testid="invalid"]').element);
  });

  it('should not focus on a rising error count unless autoFocus is set', async () => {
    wrapper = createWrapper(
      { errors: { count: 0 } },
      { default: '<input data-testid="invalid" aria-invalid="true" />' },
    );

    await wrapper.setProps({ errors: { count: 1 } });
    await flushPromises();

    expect(document.activeElement).not.toBe(wrapper.find('[data-testid="invalid"]').element);
  });

  it('should not refocus when the error count changes but was already non-zero', async () => {
    wrapper = createWrapper(
      { errors: { autoFocus: true, count: 1 } },
      { default: '<input data-testid="invalid" aria-invalid="true" />' },
    );

    await wrapper.setProps({ errors: { autoFocus: true, count: 2 } });
    await flushPromises();

    expect(document.activeElement).not.toBe(wrapper.find('[data-testid="invalid"]').element);
  });

  it('should keep the minimum content height unless the layout group opts out', () => {
    wrapper = createWrapper();
    expect(wrapper.find('.min-h-\\[50vh\\]').exists()).toBe(true);

    wrapper.unmount();
    wrapper = createWrapper({ layout: { autoHeight: true } });
    expect(wrapper.find('.min-h-\\[50vh\\]').exists()).toBe(false);
  });

  describe('cancel button', () => {
    it('should cancel straight away when the caller did not ask to be prompted', async () => {
      wrapper = createWrapper();

      await wrapper.find('[data-testid="cancel"]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
      expect(wrapper.find('[data-testid="inline-confirm"]').exists()).toBe(false);
    });

    it('should ask in its own footer rather than cancel when the caller asked to be prompted', async () => {
      wrapper = createWrapper({ promptOnClose: true });

      await wrapper.find('[data-testid="cancel"]').trigger('click');

      expect(wrapper.emitted('cancel')).toBeUndefined();
      expect(wrapper.find('[data-testid="inline-confirm"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="cancel"]').exists()).toBe(false);
      expect(get(useConfirmStore().visible)).toBe(false);
    });

    it('should cancel once discarding is confirmed', async () => {
      wrapper = createWrapper({ promptOnClose: true });

      await wrapper.find('[data-testid="cancel"]').trigger('click');
      await wrapper.find('[data-testid="inline-confirm-accept"]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should stay open with its buttons back when the user keeps editing', async () => {
      wrapper = createWrapper({ promptOnClose: true });

      await wrapper.find('[data-testid="cancel"]').trigger('click');
      await wrapper.find('[data-testid="inline-confirm-cancel"]').trigger('click');

      expect(wrapper.emitted('cancel')).toBeUndefined();
      expect(wrapper.find('[data-testid="cancel"]').exists()).toBe(true);
    });

    it('should not still be asking when reopened', async () => {
      wrapper = createWrapper({ promptOnClose: true });

      await wrapper.find('[data-testid="cancel"]').trigger('click');
      await wrapper.setProps({ display: false });
      await wrapper.setProps({ display: true });

      expect(wrapper.find('[data-testid="inline-confirm"]').exists()).toBe(false);
    });
  });

  describe('save failure', () => {
    it('should name the failure in the header without a retry, since confirm is the retry', () => {
      wrapper = createWrapper({ failure: new Error('database locked'), failureTitle: 'Could not save' });

      const strip = wrapper.find('[data-testid="big-dialog-failure"]');
      expect(strip.text()).toContain('Could not save');
      expect(strip.text()).toContain('database locked');
      expect(strip.find('[data-testid="failure-strip-retry"]').exists()).toBe(false);
    });

    it('should show nothing while there is no failure', () => {
      wrapper = createWrapper({ failureTitle: 'Could not save' });

      expect(wrapper.find('[data-testid="big-dialog-failure"]').exists()).toBe(false);
    });
  });

  describe('dismissed from the overlay stack, as the back gesture does', () => {
    function createSheet(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof BigDialog>> {
      return createWrapper(props, {}, { realSheet: true });
    }

    it('should cancel a plain dialog', () => {
      wrapper = createSheet();

      expect(useOverlayStack().dismissTop()).toBe(true);
      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should leave nothing to dismiss while it is not displayed', () => {
      wrapper = createSheet({ display: false });

      expect(useOverlayStack().dismissTop()).toBe(false);
    });

    it('should swallow the gesture without cancelling a persistent dialog', () => {
      wrapper = createSheet({ persistent: true });

      expect(useOverlayStack().dismissTop()).toBe(true);
      expect(wrapper.emitted('cancel')).toBeUndefined();
    });

    it('should keep swallowing the gesture after turning persistent while open', async () => {
      wrapper = createSheet({ persistent: false });

      await wrapper.setProps({ persistent: true });

      expect(useOverlayStack().dismissTop()).toBe(true);
      expect(wrapper.emitted('cancel')).toBeUndefined();
    });

    it('should ask in its footer rather than cancel when the caller asked to be prompted', async () => {
      wrapper = createSheet({ promptOnClose: true });

      expect(useOverlayStack().dismissTop()).toBe(true);
      await nextTick();
      expect(wrapper.emitted('cancel')).toBeUndefined();
      // the real sheet teleports its content out of the wrapper
      expect(document.body.querySelector('[data-testid="inline-confirm"]')).not.toBeNull();
    });

    it('should stay the top layer while the discard prompt is unanswered', () => {
      wrapper = createSheet({ promptOnClose: true });
      const { dismissTop } = useOverlayStack();

      dismissTop();

      expect(dismissTop()).toBe(true);
      expect(wrapper.emitted('cancel')).toBeUndefined();
    });

    it('should answer an open discard question with keep editing when dismissed again', async () => {
      wrapper = createSheet({ promptOnClose: true });
      const { dismissTop } = useOverlayStack();

      dismissTop();
      await nextTick();
      dismissTop();
      await nextTick();

      expect(document.body.querySelector('[data-testid="inline-confirm"]')).toBeNull();
      expect(document.body.querySelector('[data-testid="confirm"]')).not.toBeNull();
      expect(wrapper.emitted('cancel')).toBeUndefined();
    });
  });
});
