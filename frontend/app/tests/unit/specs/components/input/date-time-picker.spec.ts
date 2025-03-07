import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { DateFormat } from '@/types/date-format';
import { setupDayjs } from '@/utils/date';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createCustomPinia } from '../../../utils/create-pinia';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn().mockReturnValue({ other: {} }),
  }),
}));

describe('components/DateTimePicker.vue', () => {
  setupDayjs();
  let wrapper: VueWrapper<InstanceType<typeof DateTimePicker>>;
  let store: ReturnType<typeof useFrontendSettingsStore>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  const createWrapper = (options: ComponentMountingOptions<typeof DateTimePicker>) =>
    mount(DateTimePicker, {
      global: {
        plugins: [pinia],
        stubs: {
          RuiMenu: {
            template: '<span><slot name="activator"/><slot /></span>',
          },

          TransitionGroup: {
            template: '<span><slot /></span>',
          },
        },
      },
      ...options,
    });

  it('should show indicator when format is wrong', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: '',
      },
    });
    await nextTick();

    await wrapper.find('input').setValue('12/12/202');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeTruthy();

    await wrapper.find('input').setValue('12/12/2021');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

    await wrapper.find('input').setValue('12/12/2021 12');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeTruthy();
  });

  it('should allow seconds value to be optional', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: '',
      },
    });
    await nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
  });

  it('should allow milliseconds value to be also inputted', async () => {
    wrapper = createWrapper({
      props: {
        milliseconds: true,
        modelValue: '',
      },
    });
    await nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12:12.333');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['12/12/2021 12:12:12.333']);
  });

  it('should show trim value when the length of the input exceed the max length allowed', async () => {
    wrapper = createWrapper({
      props: {
        modelValue: '',
      },
    });
    await nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12:12');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

    await wrapper.find('input').setValue('12/12/2021 12:12:123');
    await nextTick();
    await wrapper.find('input').trigger('blur');
    await wrapper.find('input').trigger('focus');
    await nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('12/12/2021 12:12:12');
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
  });

  it('should not allow future datetime', async () => {
    const date = new Date(2023, 0, 1);

    vi.useFakeTimers();
    vi.setSystemTime(date);

    wrapper = createWrapper({
      props: { limitNow: true, modelValue: '' },
    });
    await nextTick();

    await wrapper.find('input').setValue('12/12/2023');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeTruthy();

    await wrapper.find('input').setValue('12/12/2022');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
  });

  it('should set now', async () => {
    const date = new Date(2023, 0, 1, 1, 1, 1);

    vi.useFakeTimers();
    vi.setSystemTime(date);

    wrapper = createWrapper({
      props: { limitNow: true, modelValue: '' },
    });
    await nextTick();

    await wrapper.find('[data-cy=date-time-picker__set-now-button]').trigger('click');

    await nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('01/01/2023 01:01:01');
    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['01/01/2023 01:01:01']);
  });

  it('should work with format YYYY-MM-DD', async () => {
    store = useFrontendSettingsStore(pinia);
    await store.updateSetting({
      dateInputFormat: DateFormat.YearMonthDateHourMinuteSecond,
    });

    wrapper = createWrapper({
      props: { modelValue: '12/12/2021 12:12:12' },
    });

    await nextTick();
    await flushPromises();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('2021/12/12 12:12:12');

    await wrapper.find('input').setValue('2023/06/06 12:12:12');

    await nextTick();

    expect(wrapper.emitted()).toHaveProperty('update:modelValue');
    expect(wrapper.emitted('update:modelValue')![0]).toEqual(['06/06/2023 12:12:12']);
  });

  describe('should adjust the timezone', () => {
    it('should render and emit the value correctly', async () => {
      wrapper = createWrapper({
        props: {
          modelValue: '12/12/2021 12:12:12',
        },
      });

      await nextTick();
      await flushPromises();

      expect((wrapper.find('input').element as HTMLInputElement).value).toBe('12/12/2021 12:12:12');

      await wrapper.find('.input-value').trigger('input', { value: 'Etc/GMT-7' });
      await nextTick();
      await flushPromises();

      expect((wrapper.find('input').element as HTMLInputElement).value).toBe('12/12/2021 19:12:12');

      await wrapper.find('input').setValue('');
      await nextTick();

      await wrapper.find('input').setValue('12/12/2021 23:59:12');
      await nextTick();

      expect(wrapper.emitted()).toHaveProperty('update:modelValue');
      expect(wrapper.emitted('update:modelValue')![0]).toEqual(['12/12/2021 16:59:12']);
    });

    it('should not allow future datetime', async () => {
      const date = new Date(2023, 0, 1, 0, 0, 0);

      vi.useFakeTimers();
      vi.setSystemTime(date);

      wrapper = createWrapper({
        props: { limitNow: true, modelValue: '' },
      });
      await nextTick();

      await wrapper.find('.input-value').trigger('input', { value: 'Etc/GMT-1' });
      await nextTick();

      await wrapper.find('input').setValue('01/01/2023 00:00:00');

      await nextTick();
      expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

      await wrapper.find('input').setValue('01/01/2023 00:59:59');

      await nextTick();
      expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

      await wrapper.find('input').setValue('01/01/2023 01:00:01');

      await nextTick();
      expect(wrapper.find('.text-rui-error').exists()).toBeTruthy();
    });

    it('should set input in the correct timezone', async () => {
      const date = new Date(2023, 0, 1, 5, 5, 5);

      vi.useFakeTimers();
      vi.setSystemTime(date);

      wrapper = createWrapper({
        props: { limitNow: true, modelValue: '' },
      });
      await nextTick();

      await wrapper.find('.input-value').trigger('input', { value: 'Etc/GMT-1' });
      await nextTick();

      await wrapper.find('[data-cy=date-time-picker__set-now-button]').trigger('click');

      await nextTick();

      expect((wrapper.find('input').element as HTMLInputElement).value).toBe('01/01/2023 06:05:05');
      expect(wrapper.emitted()).toHaveProperty('update:modelValue');
      expect(wrapper.emitted('update:modelValue')![0]).toEqual(['01/01/2023 05:05:05']);
    });
  });
});
