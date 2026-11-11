import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import CreateAccountPreferences from '@/modules/auth/create-account/preferences/CreateAccountPreferences.vue';
import '@test/i18n';

const { check, errorCount } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { check: vi.fn<() => Promise<boolean>>(), errorCount: ref<number>(0) };
});

const SectionStub = defineComponent({
  name: 'CreateAccountPremiumSection',
  setup(_props, { expose }) {
    expose({ errorCount, validate: check });
    return (): ReturnType<typeof h> => h('div');
  },
});

const ActionsStub = {
  emits: ['back', 'next'],
  name: 'CreateAccountStepActions',
  props: ['nextLabel', 'nextTestId', 'issueCount', 'loading'],
  template: '<div><button data-testid="back" @click="$emit(\'back\')" /><button data-testid="next" @click="$emit(\'next\')" /></div>',
};

const MenuSelectStub = {
  name: 'RuiMenuSelect',
  props: ['modelValue', 'options', 'keyAttr', 'textAttr'],
  template: '<div />',
};

function createWrapper(error: string = ''): VueWrapper {
  return mount(CreateAccountPreferences, {
    global: {
      stubs: {
        CreateAccountAnalyticsOption: true,
        CreateAccountErrorAlert: { props: ['error'], template: '<div data-testid="error">{{ error }}</div>' },
        CreateAccountPremiumSection: SectionStub,
        CreateAccountStepActions: ActionsStub,
        RuiMenuSelect: MenuSelectStub,
      },
    },
    props: {
      error,
      loading: false,
      mainCurrency: 'USD',
      premiumEnabled: false,
      premiumForm: { apiKey: '', apiSecret: '', syncDatabase: false },
      premiumShouldSync: false,
      submitUsageAnalytics: true,
    },
  });
}

describe('createAccountPreferences', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(errorCount, 0);
  });

  describe('creating the profile', () => {
    it('should confirm once the premium section passes its check', async () => {
      check.mockResolvedValue(true);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=next]').trigger('click');
      await flushPromises();

      expect(wrapper.emitted('confirm')).toHaveLength(1);
    });

    it('should hold back a half-filled premium pair and count it', async () => {
      check.mockResolvedValue(false);
      set(errorCount, 1);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=next]').trigger('click');
      await flushPromises();

      expect(wrapper.emitted('confirm')).toBeUndefined();
      expect(wrapper.findComponent({ name: 'CreateAccountStepActions' }).props('issueCount')).toBe(1);
    });
  });

  describe('the main currency', () => {
    it('should offer fiat currencies only', () => {
      const options: unknown = createWrapper().findComponent({ name: 'RuiMenuSelect' }).props('options');

      expect(options).toEqual(expect.arrayContaining([expect.objectContaining({ key: 'EUR' })]));
      expect(options).not.toEqual(expect.arrayContaining([expect.objectContaining({ key: 'BTC' })]));
    });

    it('should write the pick back to the wizard', async () => {
      const wrapper = createWrapper();

      wrapper.findComponent({ name: 'RuiMenuSelect' }).vm.$emit('update:modelValue', 'EUR');
      await nextTick();

      expect(wrapper.emitted('update:mainCurrency')?.[0]).toStrictEqual(['EUR']);
    });
  });

  it('should show the error of a failed create', () => {
    expect(createWrapper('device limit reached').find('[data-testid=error]').text()).toBe('device limit reached');
  });

  it('should show no error before a create has failed', () => {
    expect(createWrapper().find('[data-testid=error]').exists()).toBe(false);
  });
});
