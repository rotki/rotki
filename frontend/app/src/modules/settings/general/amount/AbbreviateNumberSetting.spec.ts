import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import AbbreviateNumberSetting from '@/modules/settings/general/amount/AbbreviateNumberSetting.vue';

const { abbreviate, model, writeError, writeSuccess } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    abbreviate: ref<boolean>(true),
    model: ref<number>(4),
    writeError: ref<string>(''),
    writeSuccess: ref<boolean>(false),
  };
});

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): typeof abbreviate => abbreviate,
}));

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: (): Record<string, unknown> => ({ error: writeError, model, success: writeSuccess }),
}));

const RuiMenuSelectStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue', 'options', 'successMessages', 'errorMessages', 'disabled'],
  template: '<div />',
});

function createWrapper(): VueWrapper<any> {
  return mount(AbbreviateNumberSetting, {
    global: { stubs: { RuiMenuSelect: RuiMenuSelectStub, SettingSwitch: true } },
  });
}

function select(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(RuiMenuSelectStub);
}

async function choose(wrapper: VueWrapper<any>, value: string): Promise<void> {
  select(wrapper).vm.$emit('update:modelValue', value);
  await nextTick();
}

describe('abbreviateNumberSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(abbreviate, true);
    set(model, 4);
    set(writeError, '');
    set(writeSuccess, false);
  });

  /**
   * The setting is stored as a number and the select binds strings, so the mapping has to hold in
   * both directions or the stored value stops matching any offered option.
   */
  describe('the threshold, stored as a number and selected as a string', () => {
    it('should show the stored number as a string', () => {
      set(model, 7);

      expect(select(createWrapper()).props('modelValue')).toBe('7');
    });

    it('should store the chosen string as a number', async () => {
      const wrapper = createWrapper();

      await choose(wrapper, '10');

      expect(get(model)).toBe(10);
    });

    it('should follow the setting changing elsewhere', async () => {
      const wrapper = createWrapper();

      set(model, 13);
      await nextTick();

      expect(select(wrapper).props('modelValue')).toBe('13');
    });
  });

  /**
   * The threshold counts digits while an abbreviation is defined by its power of ten, so each
   * option is the abbreviation's exponent plus one: a thousand abbreviates from four digits on.
   */
  it('should offer one option per abbreviation, at the digit count it starts', () => {
    expect(select(createWrapper()).props('options')).toEqual([
      { label: 'amount_display.abbreviation.k (k)', value: '4' },
      { label: 'amount_display.abbreviation.m (M)', value: '7' },
      { label: 'amount_display.abbreviation.b (B)', value: '10' },
      { label: 'amount_display.abbreviation.t (T)', value: '13' },
    ]);
  });

  /** The threshold means nothing while abbreviation is off. */
  describe('the toggle', () => {
    it('should disable the threshold while abbreviation is off', () => {
      set(abbreviate, false);

      expect(select(createWrapper()).props('disabled')).toBe(true);
    });

    it('should leave the threshold usable while abbreviation is on', () => {
      expect(select(createWrapper()).props('disabled')).toBe(false);
    });
  });

  describe('reporting the write', () => {
    it('should report a failed write', async () => {
      const wrapper = createWrapper();

      set(writeError, 'the backend said no');
      await nextTick();

      expect(select(wrapper).props('errorMessages')).toContain('the backend said no');
    });

    it('should drop the message once the setting changes again', async () => {
      const wrapper = createWrapper();
      set(writeError, 'the backend said no');
      await nextTick();

      set(model, 7);
      await nextTick();

      expect(select(wrapper).props('errorMessages')).toBe('');
    });
  });
});
