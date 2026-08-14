import type { ValidationErrors } from '@/modules/core/api/types/errors';
import type { PremiumDevice } from '@/modules/premium/devices/premium';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, defineComponent, h, type VNode } from 'vue';
import PremiumDeviceForm from '@/modules/premium/devices/components/PremiumDeviceForm.vue';
import '@test/i18n';

/** The stubs below declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

const textFieldStub = {
  emits: ['update:modelValue', 'blur'],
  name: 'RuiTextField',
  props: ['modelValue', 'errorMessages', 'disabled'],
  template: '<div />',
};

describe('premiumDeviceForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof PremiumDeviceForm>>;

  const device = (deviceName = 'laptop'): PremiumDevice => ({
    deviceIdentifier: 'device-1',
    deviceName,
    lastSeenAt: 1700000000,
    platform: 'linux',
    user: 'someone',
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue = 'desktop',
    props: Record<string, unknown> = {},
  ): VueWrapper<InstanceType<typeof PremiumDeviceForm>> {
    return mount(PremiumDeviceForm, {
      global: {
        stubs: {
          DateDisplay: true,
          RuiCard: { name: 'RuiCard', template: '<div><slot /></div>' },
          RuiTextField: textFieldStub,
        },
      },
      props: {
        device: device(),
        errorMessages: {} satisfies ValidationErrors,
        modelValue,
        ...props,
      },
    });
  }

  function field(): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>('[data-testid=premium-device-name]');
  }

  function messages(): string[] {
    const value: unknown = field().props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(value: string): Promise<void> {
    const input = field();
    input.vm.$emit('update:modelValue', value);
    input.vm.$emit('blur');
    await vi.advanceTimersToNextTimerAsync();
  }

  it('should pass validation for a non-empty name that differs from the current one', async () => {
    wrapper = createWrapper('desktop');
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(true);
  });

  it('should fail validation when the name is empty', async () => {
    wrapper = createWrapper('');
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should treat a whitespace-only name as empty', async () => {
    wrapper = createWrapper('   ');
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should fail validation when the name equals the current device name', async () => {
    wrapper = createWrapper('laptop');
    await vi.advanceTimersToNextTimerAsync();

    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should compare against the device name captured at setup, not the current prop', async () => {
    wrapper = createWrapper('desktop', { device: device('laptop') });
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.setProps({ device: device('renamed') });
    await vi.advanceTimersToNextTimerAsync();

    // The snapshot is still 'laptop', so the new prop value is accepted...
    await edit('renamed');
    expect(await wrapper.vm.validate()).toBe(true);

    // ...and the value the prop no longer holds is still rejected.
    await edit('laptop');
    expect(await wrapper.vm.validate()).toBe(false);
  });

  it('should show no message before anything is edited', async () => {
    wrapper = createWrapper('');
    await vi.advanceTimersToNextTimerAsync();

    expect(messages()).toEqual([]);
  });

  it('should report the required message once validate runs', async () => {
    wrapper = createWrapper('');
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages()).toEqual(['premium_devices.form.device_name.error.required']);
  });

  it('should report the not-equal message once validate runs', async () => {
    wrapper = createWrapper('laptop');
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.vm.validate();
    await vi.advanceTimersToNextTimerAsync();

    expect(messages()).toEqual(['premium_devices.form.device_name.error.not_equal']);
  });

  it('should show the required message once the field is emptied', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('');

    expect(messages()).toEqual(['premium_devices.form.device_name.error.required']);
  });

  it('should surface a server error reported for the field', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();
    await wrapper.vm.validate();

    await wrapper.setProps({ errorMessages: { deviceName: ['taken already'] } satisfies ValidationErrors });
    await vi.advanceTimersToNextTimerAsync();

    expect(messages()).toEqual(['taken already']);
  });

  /*
   * A parent that holds the name in a real ref, so the write out and the echo back are both real.
   * `mountModelForm` does not fit here: it is typed for an object payload, and this form's model is
   * a bare string bridged through a writable computed.
   */
  function mountUnderParent(initial = 'desktop'): { name: () => string; parent: VueWrapper } {
    const name = ref<string>(initial);
    const parent = defineComponent({
      setup(): () => VNode {
        return () => h(PremiumDeviceForm, {
          'device': device(),
          'errorMessages': {} satisfies ValidationErrors,
          'modelValue': get(name),
          'onUpdate:modelValue': (value: string): void => set(name, value),
        });
      },
    });

    return {
      name: (): string => get(name),
      parent: mount(parent, {
        global: {
          stubs: {
            DateDisplay: true,
            RuiCard: { name: 'RuiCard', template: '<div><slot /></div>' },
            RuiTextField: textFieldStub,
          },
        },
      }),
    };
  }

  it('should land an edit in the model the dialog holds', async () => {
    const { name, parent } = mountUnderParent();
    await vi.advanceTimersToNextTimerAsync();

    parent.findComponent<StubInstance>('[data-testid=premium-device-name]').vm.$emit('update:modelValue', 'workstation');
    await vi.advanceTimersToNextTimerAsync();

    // The dialog saves what it reads off the model, not what the form holds.
    expect(name()).toBe('workstation');

    parent.unmount();
  });

  it('should not re-enter the value the model echoes back', async () => {
    const { name, parent } = mountUnderParent();
    await vi.advanceTimersToNextTimerAsync();

    const field = parent.findComponent<StubInstance>('[data-testid=premium-device-name]');
    field.vm.$emit('update:modelValue', 'workstation');
    await vi.advanceTimersToNextTimerAsync();

    // The echo travels model -> state, which is the loop the core guards with isEqual.
    expect(field.props('modelValue')).toBe('workstation');
    expect(name()).toBe('workstation');

    parent.unmount();
  });

  it('should write an edit back into the model', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersToNextTimerAsync();

    await edit('workstation');

    expect(wrapper.emitted<[string]>('update:modelValue')?.at(-1)).toEqual(['workstation']);
  });

  it('should flag stateUpdated once a field is edited', async () => {
    wrapper = createWrapper();
    // Settle the mounted work first, so what follows is the only edit in play.
    await vi.advanceTimersByTimeAsync(600);

    await edit('workstation');

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).toEqual([true]);
  });

  it('should not flag stateUpdated before anything is edited', async () => {
    wrapper = createWrapper();
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.emitted('update:stateUpdated')?.at(-1)).not.toEqual([true]);
  });
});
