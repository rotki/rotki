import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, shallowRef, type VNode } from 'vue';
import CreateAccountPremiumSection from '@/modules/auth/create-account/preferences/CreateAccountPremiumSection.vue';
import '@test/i18n';

const { check, errorCount } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { check: vi.fn<() => Promise<boolean>>(), errorCount: ref<number>(0) };
});

const FormStub = defineComponent({
  name: 'CreateAccountPremiumForm',
  props: { optional: { default: false, type: Boolean } },
  setup(_props, { expose }) {
    expose({ errorCount, validate: check });
    return (): ReturnType<typeof h> => h('div');
  },
});

interface ExposedSection {
  validate: () => Promise<boolean>;
}

function isExposedSection(value: unknown): value is ExposedSection {
  return typeof value === 'object' && value !== null && typeof Reflect.get(value, 'validate') === 'function';
}

interface Harness {
  wrapper: VueWrapper;
  section: () => ExposedSection;
}

function createHarness(expanded: boolean): Harness {
  const exposed = shallowRef<unknown>();
  const parent = defineComponent({
    setup(): () => VNode {
      return () => h(CreateAccountPremiumSection, {
        expanded,
        form: { apiKey: '', apiSecret: '', syncDatabase: false },
        loading: false,
        ref: exposed,
        shouldSync: false,
      });
    },
  });
  const wrapper = mount(parent, {
    global: {
      stubs: {
        CreateAccountPremiumForm: FormStub,
        RuiCheckbox: { props: ['modelValue'], template: '<div><slot /></div>' },
        RuiIcon: true,
      },
    },
  });
  return {
    section: (): ExposedSection => {
      const value = get(exposed);
      assert(isExposedSection(value), 'the section exposes no validate()');
      return value;
    },
    wrapper,
  };
}

describe('createAccountPremiumSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should keep the credentials out of sight until it is opened', () => {
    const { wrapper } = createHarness(false);

    expect(wrapper.find('[data-testid=create-account-premium-section]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=create-account-premium-toggle]').attributes('aria-expanded')).toBe('false');
  });

  it('should ask to open when its toggle is pressed', async () => {
    const { wrapper } = createHarness(false);

    await wrapper.find('[data-testid=create-account-premium-toggle]').trigger('click');

    expect(wrapper.findComponent(CreateAccountPremiumSection).emitted('update:expanded')?.[0]).toStrictEqual([true]);
  });

  it('should treat the credentials as optional', () => {
    const { wrapper } = createHarness(true);

    expect(wrapper.findComponent({ name: 'CreateAccountPremiumForm' }).props('optional')).toBe(true);
  });

  describe('checking the section', () => {
    it('should pass a closed section without checking what it holds', async () => {
      const { section } = createHarness(false);

      await expect(section().validate()).resolves.toBe(true);
      expect(check).not.toHaveBeenCalled();
    });

    it('should defer to the credentials once open', async () => {
      check.mockResolvedValue(false);
      const { section } = createHarness(true);

      await expect(section().validate()).resolves.toBe(false);
      expect(check).toHaveBeenCalledTimes(1);
    });
  });
});
