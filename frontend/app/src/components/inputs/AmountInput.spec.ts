import { createCustomPinia } from '@test/utils/create-pinia';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AmountInput from '@/components/inputs/AmountInput.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

vi.mock('@/composables/api/settings/settings-api', (): Record<string, unknown> => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn().mockReturnValue({
      other: {
        frontendSettings: {
          thousandSeparator: ',',
          decimalSeparator: '.',
        },
      },
    }),
  }),
}));

describe('amount-input', () => {
  let wrapper: VueWrapper<InstanceType<typeof AmountInput>>;
  let store: ReturnType<typeof useFrontendSettingsStore>;
  let pinia: Pinia;

  beforeEach((): void => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof AmountInput>): VueWrapper<InstanceType<typeof AmountInput>> =>
    mount(AmountInput, {
      global: {
        plugins: [pinia],
      },
      ...options,
    });

  it('should format the numbers', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: '',
      },
    });
    await nextTick();

    await wrapper.find('input').setValue('100000');
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('100,000');

    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['100000']);
  });

  it('should use prop value', async () => {
    wrapper = createWrapper({
      props: { modelValue: '500000' },
    });
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('500,000');

    await wrapper.setProps({ modelValue: '100000.123' });
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('100,000.123');
  });

  it('should works with different thousandSeparator and decimalSeparator', async () => {
    store = useFrontendSettingsStore(pinia);

    store.update({
      thousandSeparator: '.',
      decimalSeparator: ',',
    });

    wrapper = createWrapper({
      props: { modelValue: '500000' },
    });
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('500.000');

    await wrapper.setProps({ modelValue: '100000.123' });
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('100.000,123');

    await wrapper.find('input').setValue('');
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('');

    await wrapper.find('input').setValue('500000.123');
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('500.000,123');

    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['500000.123']);
  });

  it('should remove leading zeros', async () => {
    wrapper = createWrapper({
      props: { modelValue: '' },
    });
    await nextTick();

    await wrapper.setProps({ modelValue: '0123' });
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('123');

    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['123']);
  });

  it('should emit correct value', async () => {
    wrapper = createWrapper({
      props: { modelValue: '' },
    });
    await nextTick();

    await wrapper.find('input').setValue('100000');
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('100,000');

    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['100000']);

    await wrapper.find('input').setValue('');
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('');

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['']);

    await wrapper.find('input').setValue('5555abcde');
    await nextTick();

    expect(wrapper.find<HTMLInputElement>('input').element.value).toBe('5,555');

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['5555']);
  });
});
