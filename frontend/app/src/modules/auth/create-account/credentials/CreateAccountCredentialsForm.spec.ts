import type { StubInstance } from '@test/utils/component-vm';
import type { LoginCredentials } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, describe, expect, it } from 'vitest';
import { defineComponent, h, ref, shallowRef, type VNode } from 'vue';
import CreateAccountCredentialsForm from '@/modules/auth/create-account/credentials/CreateAccountCredentialsForm.vue';
import '@test/i18n';

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled', 'type'],
    template: '<div><input :type="type" :aria-invalid="errorMessages && errorMessages.length > 0 ? \'true\' : \'false\'" /><slot name="append" /></div>',
  };
}

const ButtonStub = {
  emits: ['click'],
  template: '<button type="button" @click="$emit(\'click\')"><slot /></button>',
};

const USERNAME = 'create-account-username';
const PASSWORD = 'create-account-password';
const PASSWORD_REPEAT = 'create-account-password-repeat';
const USER_PROMPTED = 'create-account-user-prompted';
const REVEAL = 'create-account-password-reveal';

interface State {
  credentials: LoginCredentials;
  passwordConfirm: string;
  userPrompted: boolean;
}

interface ExposedForm {
  validate: () => Promise<boolean>;
  errorCount: number;
}

interface Harness {
  wrapper: VueWrapper;
  form: () => ExposedForm;
  credentials: () => LoginCredentials;
}

function filled(): State {
  return {
    credentials: { password: 'password', username: 'user' },
    passwordConfirm: 'password',
    userPrompted: true,
  };
}

function blank(): State {
  return {
    credentials: { password: '', username: '' },
    passwordConfirm: '',
    userPrompted: false,
  };
}

function isExposedForm(value: unknown): value is ExposedForm {
  return typeof value === 'object' && value !== null && typeof Reflect.get(value, 'validate') === 'function';
}

function createHarness(initial: State = filled()): Harness {
  const form = ref<LoginCredentials>(initial.credentials);
  const passwordConfirm = ref<string>(initial.passwordConfirm);
  const userPrompted = ref<boolean>(initial.userPrompted);
  const exposed = shallowRef<unknown>();

  const parent = defineComponent({
    setup(): () => VNode {
      return () => h(CreateAccountCredentialsForm, {
        'form': get(form),
        'loading': false,
        'onUpdate:form': (value: LoginCredentials): void => set(form, value),
        'onUpdate:passwordConfirm': (value: string): void => set(passwordConfirm, value),
        'onUpdate:userPrompted': (value: boolean): void => set(userPrompted, value),
        'passwordConfirm': get(passwordConfirm),
        'ref': exposed,
        'userPrompted': get(userPrompted),
      });
    },
  });

  const wrapper = mount(parent, {
    attachTo: document.body,
    global: {
      stubs: {
        RuiButton: ButtonStub,
        RuiCheckbox: inputStub('RuiCheckbox'),
        RuiIcon: true,
        RuiTextField: inputStub('RuiTextField'),
      },
    },
  });

  return {
    credentials: (): LoginCredentials => get(form),
    form: (): ExposedForm => {
      const value = get(exposed);
      assert(isExposedForm(value), 'the form exposes no validate()');
      return value;
    },
    wrapper,
  };
}

function field(harness: Harness, testId: string): VueWrapper<StubInstance> {
  const match = harness.wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
  assert(match.exists(), `no field with test id ${testId} is rendered`);
  return match;
}

function messages(harness: Harness, testId: string): string[] {
  const value: unknown = field(harness, testId).props('errorMessages');
  assert(Array.isArray(value));
  return value.map(String);
}

async function edit(harness: Harness, testId: string, value: string | boolean): Promise<void> {
  field(harness, testId).vm.$emit('update:modelValue', value);
  await nextTick();
}

describe('createAccountCredentialsForm', () => {
  it('should show no message on an untouched blank form', async () => {
    const harness = createHarness(blank());
    await nextTick();

    expect(messages(harness, USERNAME)).toStrictEqual([]);
    expect(messages(harness, PASSWORD)).toStrictEqual([]);
    expect(messages(harness, PASSWORD_REPEAT)).toStrictEqual([]);
    expect(messages(harness, USER_PROMPTED)).toStrictEqual([]);
  });

  describe('checking the step', () => {
    it('should let a filled form through', async () => {
      const harness = createHarness();

      await expect(harness.form().validate()).resolves.toBe(true);
    });

    it('should hold a blank form back and reveal an error on every field', async () => {
      const harness = createHarness(blank());

      await expect(harness.form().validate()).resolves.toBe(false);
      expect(harness.form().errorCount).toBe(4);
      expect(messages(harness, USERNAME)).not.toStrictEqual([]);
      expect(messages(harness, USER_PROMPTED)).toStrictEqual(['create_account.credentials.validation.check_prompt']);
    });

    it('should move focus to the first field holding an error', async () => {
      const harness = createHarness({ ...filled(), passwordConfirm: 'different' });

      await harness.form().validate();

      expect(document.activeElement?.closest('[data-testid]')?.getAttribute('data-testid')).toBe(PASSWORD_REPEAT);
    });

    /** Strength only advises: a short password is a warning, never a reason to stop. */
    it('should let a weak password through', async () => {
      const harness = createHarness({ ...filled(), credentials: { password: 'a', username: 'user' }, passwordConfirm: 'a' });

      await expect(harness.form().validate()).resolves.toBe(true);
    });
  });

  describe('username', () => {
    it.each([
      ['user name'],
      ['user@name'],
      ['user/name'],
    ])('should reject %s', async (username) => {
      const harness = createHarness();
      await edit(harness, USERNAME, username);

      expect(messages(harness, USERNAME)).toStrictEqual(['create_account.credentials.validation.valid_username']);
    });

    it.each([
      ['user_name'],
      ['user.name'],
      ['user-name'],
      ['User1'],
    ])('should accept %s', async (username) => {
      const harness = createHarness();
      await edit(harness, USERNAME, username);

      expect(messages(harness, USERNAME)).toStrictEqual([]);
    });

    it('should write an edit back to the wizard model', async () => {
      const harness = createHarness();
      await edit(harness, USERNAME, 'typed');

      expect(harness.credentials().username).toBe('typed');
    });
  });

  describe('password confirmation', () => {
    it('should report a confirmation that differs', async () => {
      const harness = createHarness();
      await edit(harness, PASSWORD_REPEAT, 'different');

      expect(messages(harness, PASSWORD_REPEAT)).toStrictEqual([
        'create_account.credentials.validation.password_confirmation_mismatch',
      ]);
    });

    it('should clear the mismatch when the password is edited to match', async () => {
      const harness = createHarness();
      await edit(harness, PASSWORD_REPEAT, 'different');

      await edit(harness, PASSWORD, 'different');

      expect(messages(harness, PASSWORD_REPEAT)).toStrictEqual([]);
    });

    it('should report both messages when the confirmation is cleared', async () => {
      const harness = createHarness();
      await edit(harness, PASSWORD_REPEAT, '');

      expect(messages(harness, PASSWORD_REPEAT)).toStrictEqual([
        'create_account.credentials.validation.password_confirmation_mismatch',
        'create_account.credentials.validation.non_empty_password_confirmation',
      ]);
    });
  });

  describe('showing the password', () => {
    it('should mask the password until it is shown', async () => {
      const harness = createHarness();

      expect(field(harness, PASSWORD).props('type')).toBe('password');

      await harness.wrapper.find(`[data-testid=${REVEAL}]`).trigger('click');

      expect(field(harness, PASSWORD).props('type')).toBe('text');
    });

    it('should hide the repeat field while the password is shown', async () => {
      const harness = createHarness();

      await harness.wrapper.find(`[data-testid=${REVEAL}]`).trigger('click');

      expect(harness.wrapper.find(`[data-testid=${PASSWORD_REPEAT}]`).exists()).toBe(false);
    });

    it('should not require the confirmation while the password is shown', async () => {
      const harness = createHarness({ ...filled(), passwordConfirm: '' });

      await harness.wrapper.find(`[data-testid=${REVEAL}]`).trigger('click');

      await expect(harness.form().validate()).resolves.toBe(true);
    });

    it('should require the confirmation again once the password is masked', async () => {
      const harness = createHarness({ ...filled(), passwordConfirm: '' });
      const reveal = harness.wrapper.find(`[data-testid=${REVEAL}]`);

      await reveal.trigger('click');
      await reveal.trigger('click');

      await expect(harness.form().validate()).resolves.toBe(false);
    });
  });

  describe('the strength hint', () => {
    it('should rate the password as it is typed', async () => {
      const harness = createHarness(blank());
      const meter = (): string | undefined => harness.wrapper.find('[data-testid=create-account-password-strength]').attributes('data-strength');

      expect(meter()).toBe('empty');

      await edit(harness, PASSWORD, 'a much longer passphrase');

      expect(meter()).toBe('strong');
    });
  });
});
