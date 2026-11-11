import type { LoginCredentials } from '@/modules/auth/login';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref } from 'vue';
import CreateAccountCredentials from '@/modules/auth/create-account/credentials/CreateAccountCredentials.vue';
import '@test/i18n';

const { check, errorCount } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { check: vi.fn<() => Promise<boolean>>(), errorCount: ref<number>(0) };
});

/** Stands in for the form, keeping only what the step reads off it: `check()` and the error count. */
const FormStub = defineComponent({
  name: 'CreateAccountCredentialsForm',
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

function createWrapper(mode: 'create' | 'restore' = 'create'): VueWrapper {
  return mount(CreateAccountCredentials, {
    global: {
      stubs: {
        CreateAccountCredentialsForm: FormStub,
        CreateAccountStepActions: ActionsStub,
        RuiAlert: { template: '<div><slot /></div>' },
      },
    },
    props: {
      form: ref<LoginCredentials>({ password: '', username: '' }).value,
      loading: false,
      mode,
      passwordConfirm: '',
      userPrompted: false,
    },
  });
}

function issueCount(wrapper: VueWrapper): unknown {
  return wrapper.findComponent({ name: 'CreateAccountStepActions' }).props('issueCount');
}

describe('createAccountCredentials', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(errorCount, 0);
  });

  describe('continuing', () => {
    it('should move on once the form passes its check', async () => {
      check.mockResolvedValue(true);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=next]').trigger('click');
      await flushPromises();

      expect(wrapper.emitted('next')).toHaveLength(1);
    });

    it('should stay while the form holds an error', async () => {
      check.mockResolvedValue(false);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=next]').trigger('click');
      await flushPromises();

      expect(check).toHaveBeenCalledTimes(1);
      expect(wrapper.emitted('next')).toBeUndefined();
    });
  });

  describe('the issue count', () => {
    it('should stay hidden before the first Continue, even with errors pending', async () => {
      set(errorCount, 3);
      const wrapper = createWrapper();
      await nextTick();

      expect(issueCount(wrapper)).toBe(0);
    });

    it('should follow the form\'s errors after a Continue', async () => {
      check.mockResolvedValue(false);
      set(errorCount, 3);
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=next]').trigger('click');
      await flushPromises();

      expect(issueCount(wrapper)).toBe(3);

      set(errorCount, 1);
      await nextTick();

      expect(issueCount(wrapper)).toBe(1);
    });
  });

  it('should hand Back to the wizard', async () => {
    const wrapper = createWrapper();

    await wrapper.find('[data-testid=back]').trigger('click');

    expect(wrapper.emitted('back')).toHaveLength(1);
  });

  describe('the guidance above the form', () => {
    it('should warn about the original password on a restore', () => {
      const wrapper = createWrapper('restore');

      expect(wrapper.find('[data-testid=create-account-restore-password-warning]').text())
        .toBe('create_account.credentials.password_sync_requirement');
    });

    it('should explain what the password protects on a create', () => {
      const wrapper = createWrapper('create');

      expect(wrapper.find('[data-testid=create-account-restore-password-warning]').exists()).toBe(false);
      expect(wrapper.text()).toContain('create_account.credentials.description');
    });
  });
});
