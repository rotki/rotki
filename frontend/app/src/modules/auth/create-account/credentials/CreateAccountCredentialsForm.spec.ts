import type { LoginCredentials } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import { type ComponentPublicInstance, defineComponent, h, ref, type VNode } from 'vue';
import CreateAccountCredentialsForm from '@/modules/auth/create-account/credentials/CreateAccountCredentialsForm.vue';
import '@test/i18n';

/**
 * Characterization of the vuelidate rules, written before the zod migration.
 *
 * The seam is the four models the wizard binds - `form`, `passwordConfirm`, `userPrompted` and the
 * `valid` flag that gates Continue - plus the `error-messages` each field receives. The form exposes
 * no `validate()`, so `valid` is the whole contract: the wizard's step dead-locks if it stops being
 * written, and every e2e spec that creates an account rides on this form.
 */

/** The stubs declare their props at runtime, so their instances are typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

function inputStub(name: string): Record<string, unknown> {
  return {
    emits: ['update:modelValue'],
    name,
    props: ['modelValue', 'errorMessages', 'disabled'],
    template: '<div />',
  };
}

const USERNAME = 'create-account__fields__username';
const PASSWORD = 'create-account__fields__password';
const PASSWORD_REPEAT = 'create-account__fields__password-repeat';
const USER_PROMPTED = 'create-account__boxes__user-prompted';

interface State {
  credentials: LoginCredentials;
  passwordConfirm: string;
  userPrompted: boolean;
}

interface Harness {
  wrapper: VueWrapper;
  /** The credentials as the wizard holds them, after every write the form has made. */
  credentials: () => LoginCredentials;
  /** The flag that gates the wizard's Continue button. */
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
    // `valid` starts true so a test asserting it turns false cannot pass on the initial value alone.
    const valid = ref<boolean>(true);

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

    // Vuelidate reports every failing rule, so an emptied username fails the regex as well.
    it('should report both of its messages when cleared', async () => {
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

    // The rule reads the password off the form model, so editing the password has to move the
    // confirmation's verdict too. This is the cross-field pair the zod schema must reproduce.
    it('should clear the mismatch when the password is edited to match', async () => {
      harness = createHarness();
      await edit(PASSWORD_REPEAT, 'different');
      expect(harness.valid()).toBe(false);

      await edit(PASSWORD, 'different');

      expect(messages(PASSWORD_REPEAT)).toStrictEqual([]);
      expect(harness.valid()).toBe(true);
    });

    // Characterizing, NOT endorsing. `$errors` is `$dirty ? $silentErrors : []`, and editing the
    // password does not make the *confirmation* field dirty. So Continue goes dead with no message
    // anywhere on screen, and the user has to touch the confirmation to find out why.
    // Pinned as-is so the migration reproduces it deliberately rather than changing it by accident;
    // flipping it is a one-line decision once the swap lands.
    it('should turn valid off with no message when the password is edited away from the confirmation', async () => {
      harness = createHarness();
      await edit(PASSWORD, 'changed');

      expect(harness.valid()).toBe(false);
      expect(messages(PASSWORD_REPEAT)).toStrictEqual([]);
      expect(messages(PASSWORD)).toStrictEqual([]);
    });

    it('should surface the mismatch as soon as the confirmation itself is touched', async () => {
      harness = createHarness();
      await edit(PASSWORD, 'changed');
      // Re-emitting the value it already holds would not make it dirty, so the user has to actually
      // change something for the message to appear.
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
