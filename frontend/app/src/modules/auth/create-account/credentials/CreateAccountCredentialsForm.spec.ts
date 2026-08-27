import type { StubInstance } from '@test/utils/component-vm';
import type { LoginCredentials } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import CreateAccountCredentialsForm from '@/modules/auth/create-account/credentials/CreateAccountCredentialsForm.vue';
import '@test/i18n';

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

const USERNAME = 'create-account-username';
const PASSWORD = 'create-account-password';
const PASSWORD_REPEAT = 'create-account-password-repeat';
const USER_PROMPTED = 'create-account-user-prompted';

interface State {
  credentials: LoginCredentials;
  passwordConfirm: string;
  userPrompted: boolean;
}

interface Harness {
  wrapper: VueWrapper;
  credentials: () => LoginCredentials;
  valid: () => boolean;
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

describe('createAccountCredentialsForm', () => {
  let harness: Harness;

  afterEach(() => {
    harness?.wrapper.unmount();
  });

  function createHarness(initial: State = filled()): Harness {
    const form = ref<LoginCredentials>(initial.credentials);
    const passwordConfirm = ref<string>(initial.passwordConfirm);
    const userPrompted = ref<boolean>(initial.userPrompted);
    const valid = ref<boolean>(true);
    expect(get(valid)).toBe(true);

    const parent = defineComponent({
      setup(): () => VNode {
        return () => h(CreateAccountCredentialsForm, {
          'form': get(form),
          'loading': false,
          'onUpdate:form': (value: LoginCredentials): void => set(form, value),
          'onUpdate:passwordConfirm': (value: string): void => set(passwordConfirm, value),
          'onUpdate:userPrompted': (value: boolean): void => set(userPrompted, value),
          'onUpdate:valid': (value: boolean): void => set(valid, value),
          'passwordConfirm': get(passwordConfirm),
          'userPrompted': get(userPrompted),
          'valid': get(valid),
        });
      },
    });

    const wrapper = mount(parent, {
      global: {
        stubs: {
          RuiCheckbox: inputStub('RuiCheckbox'),
          RuiRevealableTextField: inputStub('RuiRevealableTextField'),
          RuiTextField: inputStub('RuiTextField'),
        },
      },
    });

    return {
      credentials: (): LoginCredentials => get(form),
      valid: (): boolean => get(valid),
      wrapper,
    };
  }

  function field(testId: string): VueWrapper<StubInstance> {
    const match = harness.wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
    assert(match.exists(), `no field with test id ${testId} is rendered`);
    return match;
  }

  function messages(testId: string): string[] {
    const value: unknown = field(testId).props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function edit(testId: string, value: string | boolean): Promise<void> {
    field(testId).vm.$emit('update:modelValue', value);
    await nextTick();
  }

  it('should expose no validate() of its own, leaving the emitted valid flag as the whole contract', () => {
    harness = createHarness();
    const form = harness.wrapper.findComponent(CreateAccountCredentialsForm);

    expect(form.exists()).toBe(true);
    expect(form.vm).not.toHaveProperty('validate');
  });

  it('should report valid when every field is filled and the prompt is checked', async () => {
    harness = createHarness();
    await nextTick();

    expect(harness.valid()).toBe(true);
  });

  it('should report invalid on an untouched blank form', async () => {
    harness = createHarness(blank());
    await nextTick();

    expect(harness.valid()).toBe(false);
  });

  it.each([
    [USERNAME, ''],
    [PASSWORD, ''],
    [PASSWORD_REPEAT, ''],
    [USER_PROMPTED, false],
  ] as const)('should report invalid once %s is cleared', async (testId, cleared) => {
    harness = createHarness();
    await edit(testId, cleared);

    expect(harness.valid()).toBe(false);
  });

  it('should show no message on an untouched field', async () => {
    harness = createHarness(blank());
    await nextTick();

    expect(messages(USERNAME)).toStrictEqual([]);
    expect(messages(PASSWORD)).toStrictEqual([]);
    expect(messages(PASSWORD_REPEAT)).toStrictEqual([]);
    expect(messages(USER_PROMPTED)).toStrictEqual([]);
  });

  describe('username', () => {
    it.each([
      ['user name'],
      ['user@name'],
      ['user/name'],
    ])('should reject %s', async (username) => {
      harness = createHarness();
      await edit(USERNAME, username);

      expect(harness.valid()).toBe(false);
      expect(messages(USERNAME)).toStrictEqual(['create_account.credentials.validation.valid_username']);
    });

    it.each([
      ['user_name'],
      ['user.name'],
      ['user-name'],
      ['User1'],
    ])('should accept %s', async (username) => {
      harness = createHarness();
      await edit(USERNAME, username);

      expect(harness.valid()).toBe(true);
      expect(messages(USERNAME)).toStrictEqual([]);
    });

    it('should report the regex message alongside the non-empty one when cleared', async () => {
      harness = createHarness();
      await edit(USERNAME, '');

      expect(messages(USERNAME)).toStrictEqual([
        'create_account.credentials.validation.valid_username',
        'create_account.credentials.validation.non_empty_username',
      ]);
    });

    it('should write an edit back to the wizard model', async () => {
      harness = createHarness();
      await edit(USERNAME, 'typed');

      expect(harness.credentials().username).toBe('typed');
    });
  });

  describe('password confirmation', () => {
    it('should report invalid while the confirmation differs', async () => {
      harness = createHarness();
      await edit(PASSWORD_REPEAT, 'different');

      expect(harness.valid()).toBe(false);
      expect(messages(PASSWORD_REPEAT)).toStrictEqual([
        'create_account.credentials.validation.password_confirmation_mismatch',
      ]);
    });

    it('should clear the mismatch when the password is edited to match', async () => {
      harness = createHarness();
      await edit(PASSWORD_REPEAT, 'different');
      expect(harness.valid()).toBe(false);

      await edit(PASSWORD, 'different');

      expect(messages(PASSWORD_REPEAT)).toStrictEqual([]);
      expect(harness.valid()).toBe(true);
    });

    it('should turn valid off with no message when the password is edited away from the confirmation (characterized, not endorsed)', async () => {
      harness = createHarness();
      await edit(PASSWORD, 'changed');

      expect(harness.valid()).toBe(false);
      expect(messages(PASSWORD_REPEAT)).toStrictEqual([]);
      expect(messages(PASSWORD)).toStrictEqual([]);
    });

    it('should surface the mismatch as soon as the confirmation itself is touched', async () => {
      harness = createHarness();
      await edit(PASSWORD, 'changed');
      await edit(PASSWORD_REPEAT, 'chang');

      expect(messages(PASSWORD_REPEAT)).toStrictEqual([
        'create_account.credentials.validation.password_confirmation_mismatch',
      ]);
    });

    it('should report both messages when the confirmation is cleared', async () => {
      harness = createHarness();
      await edit(PASSWORD_REPEAT, '');

      expect(messages(PASSWORD_REPEAT)).toStrictEqual([
        'create_account.credentials.validation.password_confirmation_mismatch',
        'create_account.credentials.validation.non_empty_password_confirmation',
      ]);
    });
  });

  describe('the backup prompt', () => {
    it('should show its message once unchecked', async () => {
      harness = createHarness();
      await edit(USER_PROMPTED, false);

      expect(messages(USER_PROMPTED)).toStrictEqual(['create_account.credentials.validation.check_prompt']);
    });

    it('should report valid again once re-checked', async () => {
      harness = createHarness();
      await edit(USER_PROMPTED, false);
      await edit(USER_PROMPTED, true);

      expect(harness.valid()).toBe(true);
      expect(messages(USER_PROMPTED)).toStrictEqual([]);
    });
  });
});
