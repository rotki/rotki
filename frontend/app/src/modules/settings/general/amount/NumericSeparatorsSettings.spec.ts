import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref, ref } from 'vue';
import NumericSeparatorsSettings from '@/modules/settings/general/amount/NumericSeparatorsSettings.vue';

const { useSettingModelMock } = vi.hoisted(() => ({ useSettingModelMock: vi.fn() }));
vi.mock('@/modules/settings/use-setting-model', () => ({ useSettingModel: useSettingModelMock }));

const RuiTextFieldStub = defineComponent({
  props: ['modelValue', 'successMessages', 'errorMessages', 'label'],
  emits: ['update:model-value'],
  template: `<div>
    <span class="model">{{ modelValue }}</span>
    <span class="success">{{ successMessages }}</span>
    <span class="error">{{ errorMessages }}</span>
    <span class="error-count">{{ Array.isArray(errorMessages) ? errorMessages.length : (errorMessages ? 1 : 0) }}</span>
  </div>`,
});

describe('numericSeparatorsSettings', () => {
  let thousandModel: Ref<string>;
  let decimalModel: Ref<string>;
  let thousandError: Ref<string>;
  let decimalError: Ref<string>;
  let thousandSuccess: Ref<boolean>;
  let decimalSuccess: Ref<boolean>;

  function createWrapper(): VueWrapper {
    return mount(NumericSeparatorsSettings, {
      global: { stubs: { RuiTextField: RuiTextFieldStub } },
    });
  }

  function field(wrapper: VueWrapper, index: 0 | 1): VueWrapper {
    return wrapper.findAllComponents(RuiTextFieldStub)[index];
  }

  async function input(wrapper: VueWrapper, index: 0 | 1, value: string): Promise<void> {
    field(wrapper, index).vm.$emit('update:model-value', value);
    await nextTick();
  }

  function messages(wrapper: VueWrapper, index: 0 | 1): string {
    return field(wrapper, index).find('.error').text();
  }

  beforeEach(() => {
    thousandModel = ref<string>(',');
    decimalModel = ref<string>('.');
    thousandError = ref<string>('');
    decimalError = ref<string>('');
    thousandSuccess = ref<boolean>(false);
    decimalSuccess = ref<boolean>(false);
    useSettingModelMock.mockImplementation((key: string) => (key === 'thousandSeparator'
      ? { error: thousandError, flush: vi.fn(), model: thousandModel, pending: ref(false), success: thousandSuccess }
      : { error: decimalError, flush: vi.fn(), model: decimalModel, pending: ref(false), success: decimalSuccess }));
  });

  it('should render both fields with their current values', () => {
    const wrapper = createWrapper();
    expect(field(wrapper, 0).find('.model').text()).toBe(',');
    expect(field(wrapper, 1).find('.model').text()).toBe('.');
  });

  it('should persist a valid thousand separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, ' ');
    expect(get(thousandModel)).toBe(' ');
    expect(field(wrapper, 0).find('.error-count').text()).toBe('0');
  });

  it('should persist a valid decimal separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 1, '\'');
    expect(get(decimalModel)).toBe('\'');
  });

  it('should reject a numeric separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '1');
    expect(get(thousandModel)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.cannot_be_numeric_character');
  });

  it('should reject an empty separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '');
    expect(get(thousandModel)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.empty');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.single_character');
  });

  it('should reject more than one visual character', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '..');
    expect(get(thousandModel)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.single_character');
  });

  it('should accept a multi-code-point emoji as one visual character', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '👩‍💻');
    expect(get(thousandModel)).toBe('👩‍💻');
  });

  it('should reject a decimal separator equal to the thousand separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 1, ',');
    expect(get(decimalModel)).toBe('.');
    expect(messages(wrapper, 1)).toContain('general_settings.decimal_separator.validation.cannot_be_the_same');
  });

  it('should not persist a thousand separator equal to the decimal one', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '.');
    expect(get(thousandModel)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.cannot_be_the_same');
  });

  // Regression: a rejected value stays in the field it was typed into. If that draft is what the
  // other field is compared against, the pair can be walked into two identical separators.
  it('should not persist identical separators through a rejected draft', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '.');
    expect(get(thousandModel)).toBe(',');

    await input(wrapper, 1, ',');
    expect(get(thousandModel)).not.toBe(get(decimalModel));
  });

  it('should keep the two fields error messages apart', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '1');
    expect(field(wrapper, 1).find('.error-count').text()).toBe('0');
  });

  it('should reflect external changes of both settings', async () => {
    const wrapper = createWrapper();
    set(thousandModel, '_');
    set(decimalModel, '-');
    await nextTick();
    expect(field(wrapper, 0).find('.model').text()).toBe('_');
    expect(field(wrapper, 1).find('.model').text()).toBe('-');
  });

  it('should show per-field success and error messages from the writer', async () => {
    const wrapper = createWrapper();
    set(thousandSuccess, true);
    set(decimalError, 'boom');
    await nextTick();
    expect(field(wrapper, 0).find('.success').text()).toContain('general_settings.validation.thousand_separator.success');
    expect(field(wrapper, 1).find('.error').text()).toContain('settings.not_saved: general_settings.validation.decimal_separator.error: boom');
  });
});
