import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { type Pinia, setActivePinia } from 'pinia';
import DateTimePicker from '@/components/inputs/DateTimePicker.vue';
import { DateFormat } from '@/types/date-format';
import createCustomPinia from '../../../utils/create-pinia';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn().mockReturnValue({ other: {} })
  })
}));

describe('DateTimePicker.vue', () => {
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
      ...options
    });
  };

  test('should show indicator when format is wrong', async () => {
    wrapper = createWrapper({});
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('12/12/202');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeTruthy();

    await wrapper.find('input').setValue('12/12/2021');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeFalsy();

    await wrapper.find('input').setValue('12/12/2021 12');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeTruthy();
  });

  test('should force user to input seconds value, when time value is also provided', async () => {
    wrapper = createWrapper({
      propsData: { seconds: true }
    });
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeTruthy();

    await wrapper.find('input').setValue('12/12/2021 12:12:12');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeFalsy();
  });

  test('should allow seconds value to be optional', async () => {
    wrapper = createWrapper({
      propsData: { seconds: false }
    });
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeFalsy();
  });

  test('should show trim value when the length of the input exceed the max length allowed', async () => {
    wrapper = createWrapper({
      propsData: { seconds: false }
    });
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('12/12/2021 12:12:12');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeFalsy();

    await wrapper.find('input').setValue('12/12/2021 12:12:123');
    await wrapper.vm.$nextTick();
    await wrapper.find('input').trigger('blur');
    await wrapper.find('input').trigger('focus');
    await wrapper.vm.$nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '12/12/2021 12:12:12'
    );
    expect(wrapper.find('.v-input.error--text').exists()).toBeFalsy();
  });

  test('should not allow future datetime', async () => {
    const date = new Date(2023, 0, 1);

    vi.useFakeTimers();
    vi.setSystemTime(date);

    wrapper = createWrapper({
      propsData: { limitNow: true }
    });
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('12/12/2023');
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.v-input.error--text').exists()).toBeTruthy();
  });

  test('should set now', async () => {
    const date = new Date(2023, 0, 1, 1, 1, 1);

    vi.useFakeTimers();
    vi.setSystemTime(date);

    wrapper = createWrapper({
      propsData: { limitNow: true, seconds: true }
    });
    await wrapper.vm.$nextTick();

    await wrapper
      .find('[data-cy=date-time-picker__set-now-button]')
      .trigger('click');

    await wrapper.vm.$nextTick();
    expect(wrapper.emitted().input?.[0]).toEqual(['01/01/2023 01:01:01']);
  });

  test('should work with format YYYY-MM-DD', async () => {
    store = useFrontendSettingsStore(pinia);
    await store.updateSetting({
      dateInputFormat: DateFormat.YearMonthDateHourMinuteSecond
    });

    wrapper = createWrapper({
      propsData: { value: '12/12/2021 12:12:12', seconds: true }
    });

    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '2021/12/12 12:12:12'
    );

    await wrapper.find('input').setValue('2023/12/12 23:59:59');
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted().input?.[2]).toEqual(['12/12/2023 23:59:59']);
  });

  test('should adjust the timezone', async () => {
    wrapper = createWrapper({
      stubs: {
        VMenu: {
          template: '<span><slot name="activator"/><slot /></span>'
        },
        VAutocomplete: {
          template: `
            <div>
              <input :value="value" class="search-input" type="text" @input="$emit('input', $event.value)">
            </div>
          `,
          props: {
            value: { type: String }
          }
        }
      },
      propsData: {
        value: '12/12/2021 12:12:12'
      }
    });

    await wrapper.vm.$nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '12/12/2021 12:12:12'
    );

    await wrapper
      .find('.search-input')
      .trigger('input', { value: 'Asia/Jakarta' });
    await wrapper.vm.$nextTick();
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '12/12/2021 19:12:12'
    );

    await wrapper.find('input').setValue('12/12/2021 23:59:59');
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted().input?.[2]).toEqual(['12/12/2021 16:59:59']);
  });
});
