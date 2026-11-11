import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h } from 'vue';
import CreateAccountPremium from '@/modules/auth/create-account/premium/CreateAccountPremium.vue';
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

const ActionsStub = {
  emits: ['back', 'next'],
  name: 'CreateAccountStepActions',
  props: ['nextLabel', 'nextTestId', 'issueCount', 'loading'],
  template: '<div><button data-testid="back" @click="$emit(\'back\')" /><button data-testid="next" @click="$emit(\'next\')" /></div>',
};

function createWrapper(): VueWrapper {
  return mount(CreateAccountPremium, {
    global: {
      stubs: {
        CreateAccountPremiumForm: FormStub,
        CreateAccountStepActions: ActionsStub,
      },
    },
    props: {
      form: { apiKey: '', apiSecret: '', syncDatabase: true },
      loading: false,
    },
  });
}

describe('createAccountPremium', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(errorCount, 0);
  });

  it('should require the credentials, since a restore cannot go without them', () => {
    expect(createWrapper().findComponent({ name: 'CreateAccountPremiumForm' }).props('optional')).toBe(false);
  });

  it('should move on once the credentials pass their check', async () => {
    check.mockResolvedValue(true);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=next]').trigger('click');
    await flushPromises();

    expect(wrapper.emitted('next')).toHaveLength(1);
  });

  it('should stay and count the problems while a credential is missing', async () => {
    check.mockResolvedValue(false);
    set(errorCount, 2);
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=next]').trigger('click');
    await flushPromises();

    expect(wrapper.emitted('next')).toBeUndefined();
    expect(wrapper.findComponent({ name: 'CreateAccountStepActions' }).props('issueCount')).toBe(2);
  });

  it('should hand Back to the wizard', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=back]').trigger('click');

    expect(wrapper.emitted('back')).toHaveLength(1);
  });
});
