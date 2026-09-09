import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import LanguageSetting from '@/modules/settings/general/language/LanguageSetting.vue';
import { SupportedLanguage } from '@/modules/settings/types/frontend-settings';

const { adaptiveLanguage, flush, forceUpdateMachineLanguage, lastLanguage, model, writeError, writeSuccess }
  = await vi.hoisted(async () => {
    const { ref } = await import('vue');
    return {
      adaptiveLanguage: ref<string>('en'),
      flush: vi.fn(async () => {}),
      forceUpdateMachineLanguage: ref<string>('true'),
      lastLanguage: ref<string>('en'),
      model: ref<string>('en'),
      writeError: ref<string>(''),
      writeSuccess: ref<boolean>(false),
    };
  });

vi.mock('@/modules/session/use-locale', () => ({
  useLocale: (): Record<string, unknown> => ({ adaptiveLanguage, forceUpdateMachineLanguage, lastLanguage }),
}));

vi.mock('@/modules/settings/use-setting-model', () => ({
  useSettingModel: (): Record<string, unknown> => ({ error: writeError, flush, model, success: writeSuccess }),
}));

const RuiMenuSelectStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue', 'options', 'successMessages', 'errorMessages'],
  template: '<div />',
});

const RuiCheckboxStub = defineComponent({
  emits: ['update:modelValue'],
  props: ['modelValue'],
  template: '<div />',
});

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(LanguageSetting, {
    global: {
      stubs: {
        ExternalLink: true,
        LanguageSelectorItem: true,
        RuiCheckbox: RuiCheckboxStub,
        RuiMenuSelect: RuiMenuSelectStub,
        SettingsItem: { name: 'SettingsItem', template: '<div><slot /></div>' },
      },
    },
    props,
  });
}

function select(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(RuiMenuSelectStub);
}

function checkbox(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(RuiCheckboxStub);
}

async function choose(wrapper: VueWrapper<any>, language: SupportedLanguage): Promise<void> {
  select(wrapper).vm.$emit('update:modelValue', language);
  await nextTick();
}

describe('languageSetting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(adaptiveLanguage, SupportedLanguage.EN);
    set(forceUpdateMachineLanguage, 'true');
    set(lastLanguage, SupportedLanguage.EN);
    set(model, SupportedLanguage.EN);
    set(writeError, '');
    set(writeSuccess, false);
  });

  it('should start on the language the session resolved', async () => {
    set(adaptiveLanguage, SupportedLanguage.GR);

    const wrapper = createWrapper();
    await nextTick();

    expect(select(wrapper).props('modelValue')).toBe(SupportedLanguage.GR);
  });

  it('should offer every supported language', () => {
    expect(select(createWrapper()).props('options')).toContainEqual({
      countries: ['gb', 'us'],
      identifier: SupportedLanguage.EN,
      label: 'English',
    });
  });

  /**
   * The login screen picks a language before there is an account to store it against, so it keeps
   * the choice locally instead of writing it to the user's settings.
   */
  describe('when it is the local setting', () => {
    it('should remember the choice locally', async () => {
      const wrapper = createWrapper({ useLocalSetting: true });

      await choose(wrapper, SupportedLanguage.ES);

      expect(get(lastLanguage)).toBe(SupportedLanguage.ES);
    });

    it('should not write it to the settings', async () => {
      const wrapper = createWrapper({ useLocalSetting: true });

      await choose(wrapper, SupportedLanguage.ES);

      expect(get(model)).toBe(SupportedLanguage.EN);
      expect(flush).not.toHaveBeenCalled();
    });

    it('should hide the machine language option', () => {
      expect(checkbox(createWrapper({ useLocalSetting: true })).exists()).toBe(false);
    });
  });

  /** A language change is a deliberate act, so it is written at once rather than on the debounce. */
  describe('when it is the account setting', () => {
    it('should write the choice immediately', async () => {
      const wrapper = createWrapper();

      await choose(wrapper, SupportedLanguage.ES);

      expect(get(model)).toBe(SupportedLanguage.ES);
      expect(flush).toHaveBeenCalledTimes(1);
    });

    it('should leave the local language alone', async () => {
      const wrapper = createWrapper();

      await choose(wrapper, SupportedLanguage.ES);

      expect(get(lastLanguage)).toBe(SupportedLanguage.EN);
    });
  });

  /** The preference is stored as a string, so the checkbox has to map both ways. */
  describe('the machine language preference', () => {
    it('should show it as checked while it is on', () => {
      expect(checkbox(createWrapper()).props('modelValue')).toBe(true);
    });

    it('should show it as unchecked while it is off', () => {
      set(forceUpdateMachineLanguage, 'false');

      expect(checkbox(createWrapper()).props('modelValue')).toBe(false);
    });

    it('should store it as a string when turned off', async () => {
      const wrapper = createWrapper();

      checkbox(wrapper).vm.$emit('update:modelValue', false);
      await nextTick();

      expect(get(forceUpdateMachineLanguage)).toBe('false');
    });

    it('should store it as a string when turned back on', async () => {
      set(forceUpdateMachineLanguage, 'false');
      const wrapper = createWrapper();

      checkbox(wrapper).vm.$emit('update:modelValue', true);
      await nextTick();

      expect(get(forceUpdateMachineLanguage)).toBe('true');
    });
  });

  describe('reporting the write', () => {
    it('should report a failed write', async () => {
      const wrapper = createWrapper();

      set(writeError, 'the backend said no');
      await nextTick();

      expect(select(wrapper).props('errorMessages'))
        .toContain('general_settings.language.validation.error: the backend said no');
    });

    it('should drop the message once the setting changes again', async () => {
      const wrapper = createWrapper();
      set(writeError, 'the backend said no');
      await nextTick();

      set(model, SupportedLanguage.ES);
      await nextTick();

      expect(select(wrapper).props('errorMessages')).toBe('');
    });
  });
});
