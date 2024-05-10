import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount,
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { type Pinia, setActivePinia } from 'pinia';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { DateFormat } from '@/types/date-format';
import { createCustomPinia } from '../../../utils/create-pinia';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn().mockReturnValue({ other: {} }),
  }),
}));

describe('dateTimePicker.vue', () => {
  setupDayjs();
  let wrapper: Wrapper<DateTimePicker>;
  let store: ReturnType<typeof useFrontendSettingsStore>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    useFrontendSettingsStore().$reset();
  });

  const createWrapper = (options: ThisTypedMountOptions<any>) => {
    const vuetify = new Vuetify();
    return mount(DateTimePicker, {
      pinia,
      vuetify,
      stubs: {
        RuiMenu: {
          template: '<span><slot name="activator"/><slot /></span>',
        },
        TransitionGroup: '<span><slot /></span>',
      },
      ...options,
    });
  };

  it('should show indicator when format is wrong', async () => {
    wrapper = createWrapper({});
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
    wrapper = createWrapper({});
    await nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
  });

  it('should allow milliseconds value to be also inputted', async () => {
    wrapper = createWrapper({
      propsData: {
        milliseconds: true,
      },
    });
    await nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12:12.333');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
    expect(wrapper.emitted().input?.[0]).toEqual(['12/12/2021 12:12:12.333']);
  });

  it('should show trim value when the length of the input exceed the max length allowed', async () => {
    wrapper = createWrapper({});
    await nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12:12');
    await nextTick();
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

    await wrapper.find('input').setValue('12/12/2021 12:12:123');
    await nextTick();
    await wrapper.find('input').trigger('blur');
    await wrapper.find('input').trigger('focus');
    await nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '12/12/2021 12:12:12',
    );
    expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();
  });

  it('should not allow future datetime', async () => {
    const date = new Date(2023, 0, 1);

    vi.useFakeTimers();
    vi.setSystemTime(date);

    wrapper = createWrapper({
      propsData: { limitNow: true },
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
      propsData: { limitNow: true },
    });
    await nextTick();

    await wrapper
      .find('[data-cy=date-time-picker__set-now-button]')
      .trigger('click');

    await nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '01/01/2023 01:01:01',
    );
    expect(wrapper.emitted().input?.[0]).toEqual(['01/01/2023 01:01:01']);
  });

  it('should work with format YYYY-MM-DD', async () => {
    store = useFrontendSettingsStore(pinia);
    await store.updateSetting({
      dateInputFormat: DateFormat.YearMonthDateHourMinuteSecond,
    });

    wrapper = createWrapper({
      propsData: { value: '12/12/2021 12:12:12' },
    });

    await nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '2021/12/12 12:12:12',
    );

    await wrapper.find('input').setValue('2023/06/06 12:12:12');
    await get(wrapper.vm._setupState.imask).updateValue();
    await nextTick();

    expect(wrapper.emitted().input?.[1]).toEqual(['06/06/2023 12:12:12']);
  });

  describe('should adjust the timezone', () => {
    it('should render and emit the value correctly', async () => {
      wrapper = createWrapper({
        propsData: {
          value: '12/12/2021 12:12:12',
        },
      });

      await nextTick();
      expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
        '12/12/2021 12:12:12',
      );

      await wrapper
        .find('.input-value')
        .trigger('input', { value: 'Etc/GMT-7' });
      await nextTick();
      expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
        '12/12/2021 19:12:12',
      );

      await wrapper.find('input').setValue('');
      await get(wrapper.vm._setupState.imask).updateValue();
      await nextTick();

      await wrapper.find('input').setValue('12/12/2021 23:59:12');
      await get(wrapper.vm._setupState.imask).updateValue();
      await nextTick();

      expect(wrapper.emitted().input?.[2]).toEqual(['12/12/2021 16:59:12']);
    });

    it('should not allow future datetime', async () => {
      const date = new Date(2023, 0, 1, 0, 0, 0);

      vi.useFakeTimers();
      vi.setSystemTime(date);

      wrapper = createWrapper({
        propsData: { limitNow: true },
      });
      await nextTick();

      await wrapper
        .find('.input-value')
        .trigger('input', { value: 'Etc/GMT-1' });
      await nextTick();

      await wrapper.find('input').setValue('01/01/2023 00:00:00');

      await get(wrapper.vm._setupState.imask).updateValue();
      await nextTick();
      expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

      await wrapper.find('input').setValue('01/01/2023 00:59:59');

      await get(wrapper.vm._setupState.imask).updateValue();
      await nextTick();
      expect(wrapper.find('.text-rui-error').exists()).toBeFalsy();

      await wrapper.find('input').setValue('01/01/2023 01:00:01');

      await get(wrapper.vm._setupState.imask).updateValue();
      await nextTick();
      expect(wrapper.find('.text-rui-error').exists()).toBeTruthy();
    });

    it('should set input in the correct timezone', async () => {
      const date = new Date(2023, 0, 1, 5, 5, 5);

      vi.useFakeTimers();
      vi.setSystemTime(date);

      wrapper = createWrapper({
        propsData: { limitNow: true },
      });
      await nextTick();

      await wrapper
        .find('.input-value')
        .trigger('input', { value: 'Etc/GMT-1' });
      await nextTick();

      await wrapper
        .find('[data-cy=date-time-picker__set-now-button]')
        .trigger('click');

      await nextTick();

      expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
        '01/01/2023 06:05:05',
      );
      expect(wrapper.emitted().input?.[0]).toEqual(['01/01/2023 05:05:05']);
    });
  });
});
