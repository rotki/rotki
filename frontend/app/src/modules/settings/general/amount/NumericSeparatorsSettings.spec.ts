import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, type Ref, ref } from 'vue';
import NumericSeparatorsSettings from '@/modules/settings/general/amount/NumericSeparatorsSettings.vue';

const { useSettingMock, writeManyMock } = vi.hoisted(() => ({
  useSettingMock: vi.fn(),
  writeManyMock: vi.fn(),
}));
vi.mock('@/modules/settings/settings-writer', () => ({ useSettingsWriter: (): Record<string, unknown> => ({ writeMany: writeManyMock }) }));
vi.mock('@/modules/settings/use-setting', () => ({ useSetting: useSettingMock }));

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
  let thousandSource: Ref<string>;
  let decimalSource: Ref<string>;

  function createWrapper(): VueWrapper {
    return mount(NumericSeparatorsSettings, {
      global: { stubs: { RuiTextField: RuiTextFieldStub } },
    });
  }

  function field(wrapper: VueWrapper, index: 0 | 1): VueWrapper {
    return wrapper.findAllComponents(RuiTextFieldStub)[index];
  }

  /** Types a value and lets the debounced persist run. */
  async function input(wrapper: VueWrapper, index: 0 | 1, value: string): Promise<void> {
    field(wrapper, index).vm.$emit('update:model-value', value);
    await nextTick();
    await vi.advanceTimersByTimeAsync(1600);
  }

  function messages(wrapper: VueWrapper, index: 0 | 1): string {
    return field(wrapper, index).find('.error').text();
  }

  /** The settings patch of the last write, or undefined when nothing was written. */
  function lastWrite(): Record<string, string> | undefined {
    return writeManyMock.mock.calls.at(-1)?.[0];
  }

  beforeEach(() => {
    vi.useFakeTimers();
    thousandSource = ref<string>(',');
    decimalSource = ref<string>('.');
    writeManyMock.mockReset();
    writeManyMock.mockImplementation(async (patch: Record<string, string>) => {
      // Mirror the repo: a successful write becomes the new source of truth.
      if (patch.thousandSeparator !== undefined)
        set(thousandSource, patch.thousandSeparator);
      if (patch.decimalSeparator !== undefined)
        set(decimalSource, patch.decimalSeparator);
      return { success: true };
    });
    useSettingMock.mockImplementation((key: string) => (key === 'thousandSeparator' ? thousandSource : decimalSource));
  });

  it('should render both fields with their current values', () => {
    const wrapper = createWrapper();
    expect(field(wrapper, 0).find('.model').text()).toBe(',');
    expect(field(wrapper, 1).find('.model').text()).toBe('.');
  });

  it('should persist a valid thousand separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, ' ');
    expect(get(thousandSource)).toBe(' ');
    expect(field(wrapper, 0).find('.error-count').text()).toBe('0');
  });

  it('should persist a valid decimal separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 1, '\'');
    expect(get(decimalSource)).toBe('\'');
  });

  it('should reject a numeric separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '1');
    expect(get(thousandSource)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.cannot_be_numeric_character');
  });

  it('should reject an empty separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '');
    expect(get(thousandSource)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.empty');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.single_character');
  });

  it('should reject more than one visual character', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '..');
    expect(get(thousandSource)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.single_character');
  });

  it('should accept a multi-code-point emoji as one visual character', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '👩‍💻');
    expect(get(thousandSource)).toBe('👩‍💻');
  });

  it('should reject a decimal separator equal to the thousand separator', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 1, ',');
    expect(get(decimalSource)).toBe('.');
    expect(messages(wrapper, 1)).toContain('general_settings.decimal_separator.validation.cannot_be_the_same');
  });

  it('should not persist a thousand separator equal to the decimal one', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '.');
    expect(get(thousandSource)).toBe(',');
    expect(messages(wrapper, 0)).toContain('general_settings.thousand_separator.validation.cannot_be_the_same');
  });

  it('should not persist identical separators through a rejected draft left in the field', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '.');
    expect(writeManyMock).not.toHaveBeenCalled();

    await input(wrapper, 1, ',');
    expect(get(thousandSource)).not.toBe(get(decimalSource));
  });

  it('should persist both separators in a single patch, so neither carries the other\'s pre-edit value', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '.');
    await input(wrapper, 1, ',');

    expect(writeManyMock).toHaveBeenCalledTimes(1);
    expect(lastWrite()).toStrictEqual({ decimalSeparator: ',', thousandSeparator: '.' });
  });

  it('should not write when the pair is unchanged', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, ',');
    expect(writeManyMock).not.toHaveBeenCalled();
  });

  it('should restore the stored pair when the write fails', async () => {
    writeManyMock.mockResolvedValue({ message: 'boom', success: false });
    const wrapper = createWrapper();
    await input(wrapper, 0, ';');

    expect(field(wrapper, 0).find('.model').text()).toBe(',');
    expect(field(wrapper, 0).find('.error').text()).toContain('settings.not_saved: general_settings.validation.thousand_separator.error: boom');
  });

  it('should keep the two fields error messages apart', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, '1');
    expect(field(wrapper, 1).find('.error-count').text()).toBe('0');
  });

  it('should reflect external changes of both settings', async () => {
    const wrapper = createWrapper();
    set(thousandSource, '_');
    set(decimalSource, '-');
    await nextTick();
    expect(field(wrapper, 0).find('.model').text()).toBe('_');
    expect(field(wrapper, 1).find('.model').text()).toBe('-');
  });

  it('should show a success message on both fields once the pair is written', async () => {
    const wrapper = createWrapper();
    await input(wrapper, 0, ';');
    expect(field(wrapper, 0).find('.success').text()).toContain('general_settings.validation.thousand_separator.success');
    expect(field(wrapper, 1).find('.success').text()).toContain('general_settings.validation.decimal_separator.success');
  });
});
