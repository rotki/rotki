import {
  type ThisTypedMountOptions,
  type Wrapper,
  mount
} from '@vue/test-utils';
import Vuetify from 'vuetify';
import { type Pinia, setActivePinia } from 'pinia';
import AmountInput from '@/components/inputs/AmountInput.vue';
import createCustomPinia from '../../../utils/create-pinia';

vi.mock('@/composables/api/settings/settings-api', () => ({
  useSettingsApi: vi.fn().mockReturnValue({
    setSettings: vi.fn().mockReturnValue({ other: {} })
  })
}));

describe('AmountInput.vue', () => {
  let wrapper: Wrapper<AmountInput>;
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
    return mount(AmountInput, {
      pinia,
      vuetify,
      ...options
    });
  };

  test('should format the numbers', async () => {
    wrapper = createWrapper({});
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('100000');
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '100,000'
    );

    expect(wrapper.emitted().input?.[1]).toEqual(['100000']);
  });

  test('should use prop value', async () => {
    wrapper = createWrapper({
      propsData: { value: '500000' }
    });
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '500,000'
    );

    await wrapper.setProps({ value: '100000.123' });
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '100,000.123'
    );
  });

  test('should works with different thousandSeparator and decimalSeparator', async () => {
    store = useFrontendSettingsStore(pinia);

    await store.updateSetting({
      thousandSeparator: '.',
      decimalSeparator: ','
    });

    wrapper = createWrapper({
      propsData: { value: '500000' }
    });
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '500.000'
    );

    await wrapper.setProps({ value: '100000.123' });
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '100.000,123'
    );

    await wrapper.find('input').setValue('');
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('');

    await wrapper.find('input').setValue('500000.123');
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '500.000,123'
    );

    expect(wrapper.emitted().input?.[3]).toEqual(['500000.123']);
  });

  test('should emit correct value', async () => {
    wrapper = createWrapper({});
    await wrapper.vm.$nextTick();

    await wrapper.find('input').setValue('100000');
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '100,000'
    );

    expect(wrapper.emitted().input?.[1]).toEqual(['100000']);

    await wrapper.find('input').setValue('');
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('');

    expect(wrapper.emitted().input?.[2]).toEqual(['']);

    await wrapper.find('input').setValue('5555abcde');
    await wrapper.vm.$nextTick();

    expect((wrapper.find('input').element as HTMLInputElement).value).toBe(
      '5,555'
    );

    expect(wrapper.emitted().input?.[3]).toEqual(['5555']);
  });
});
