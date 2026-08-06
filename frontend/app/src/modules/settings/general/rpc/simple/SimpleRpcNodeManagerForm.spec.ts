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
        'errorMessages': errorMessages,
        'modelValue': modelValue,
        'stateUpdated': false,
        'onUpdate:errorMessages': async (value: ValidationErrors): Promise<void> => wrapper.setProps({ errorMessages: value }),
        'onUpdate:modelValue': async (value: string): Promise<void> => wrapper.setProps({ modelValue: value }),
        'onUpdate:stateUpdated': async (value: boolean): Promise<void> => wrapper.setProps({ stateUpdated: value }),
      },
    });
  }

  it('should fail validation when the url is empty', async () => {
    wrapper = createWrapper('');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.vm.validate()).toBe(false);
  });

  it('should pass validation with a non-empty url', async () => {
    wrapper = createWrapper('https://example.com');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.vm.validate()).toBe(true);
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

  it('should display an externally reported error on the field', async () => {
    wrapper = createWrapper('https://example.com');
    await vi.advanceTimersToNextTimerAsync();

    await wrapper.find('input').setValue('https://bad-url');
    await wrapper.setProps({ errorMessages: { modelValue: ['Invalid endpoint'] } });
    await nextTick();

    expect(wrapper.find('.details .text-rui-error').text()).toBe('Invalid endpoint');
  });

  it('should reveal the error on the field when validation fails', async () => {
    wrapper = createWrapper('');
    await vi.advanceTimersToNextTimerAsync();

    expect(wrapper.find('.details .text-rui-error').exists()).toBe(false);

    wrapper.vm.validate();
    await nextTick();

    expect(wrapper.find('.details .text-rui-error').exists()).toBe(true);
  });

  it('should report the state as updated once the url is edited', async () => {
    wrapper = createWrapper('https://example.com');
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.props('stateUpdated')).toBe(false);

    await wrapper.find('input').setValue('https://example.com/rpc');
    await vi.advanceTimersByTimeAsync(600);

    expect(wrapper.props('stateUpdated')).toBe(true);
  });
});
