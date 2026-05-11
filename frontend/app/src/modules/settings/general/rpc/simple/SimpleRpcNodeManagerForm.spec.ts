import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import SimpleRpcNodeManagerForm from '@/modules/settings/general/rpc/simple/SimpleRpcNodeManagerForm.vue';

type FormInstance = InstanceType<typeof SimpleRpcNodeManagerForm>;

describe('settings/general/rpc/simple/SimpleRpcNodeManagerForm.vue', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper<FormInstance>;

  beforeAll(() => {
    pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    wrapper?.unmount();
    vi.useRealTimers();
  });

  function createWrapper(
    modelValue: string = '',
    errorMessages: ValidationErrors = {},
  ): VueWrapper<FormInstance> {
    return mount(SimpleRpcNodeManagerForm, {
      global: {
        plugins: [pinia],
      },
      props: {
        errorMessages,
        modelValue,
        'onUpdate:errorMessages': async (value: ValidationErrors): Promise<void> => wrapper.setProps({ errorMessages: value }),
        'onUpdate:modelValue': async (value: string): Promise<void> => wrapper.setProps({ modelValue: value }),
      },
    });
  }

  it('should fail validation when the url is empty', async () => {
    wrapper = createWrapper('');
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(false);
  });

  it('should pass validation with a non-empty url', async () => {
    wrapper = createWrapper('https://example.com');
    await vi.advanceTimersToNextTimerAsync();

    const valid = await wrapper.vm.validate();
    expect(valid).toBe(true);
  });

  it('should clear external error messages when the url changes', async () => {
    wrapper = createWrapper('https://bad-url', { modelValue: ['Invalid endpoint'] });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.props('errorMessages')).toEqual({ modelValue: ['Invalid endpoint'] });

    await wrapper.setProps({ modelValue: 'https://bad-url/fixed' });
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.props('errorMessages')).toEqual({});
  });

  it('should leave error messages untouched when the url is unchanged', async () => {
    const errors: ValidationErrors = { modelValue: ['Invalid endpoint'] };
    wrapper = createWrapper('https://bad-url', errors);
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.props('errorMessages')).toEqual({ modelValue: ['Invalid endpoint'] });
  });
});
