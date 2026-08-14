import type { LoginCredentials } from '@/modules/auth/login';
import type { useCustomBackend } from '@/modules/auth/login/use-custom-backend';
import type { useLoginRememberOptions } from '@/modules/auth/login/use-login-remember-options';
import type { useLogout } from '@/modules/auth/use-logout';
import type { useSavedProfiles } from '@/modules/auth/use-saved-profiles';
import type { ActionStatus } from '@/modules/core/common/action';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, ref } from 'vue';
import '@test/i18n';

/**
 * Characterization of the vuelidate rules, written before the zod migration.
 *
 * The seam is what the form exposes to `LoginScreen`: the `login` emit and its payload, the state of
 * the submit button, and the `error-messages` each field receives. The form has no `valid` model and
 * exposes no `validate()` - it gates its own submit button on `v$.$invalid` - so the button's
 * disabled state IS the validity contract here.
 *
 * `:disabled="v$.$invalid || ..."` is exactly the binding that breaks under the zod core, where
 * `form.valid` does not unwrap in a template. These tests fail loudly if that happens.
 */

const backendDisplay = ref<boolean>(false);
const backendUrl = ref<string>('');
const savedUsernames = ref<string[]>(['saved-user']);
const storedUsername = ref<string>('');

/** Typed off the real composables so a drift in any of them fails the typecheck rather than a test. */
type SavedProfilesMock = ReturnType<typeof useSavedProfiles>;

type RememberOptionsMock = ReturnType<typeof useLoginRememberOptions>;

type CustomBackendMock = ReturnType<typeof useCustomBackend>;

type LogoutMock = Pick<ReturnType<typeof useLogout>, 'logoutRemoteSession'>;

vi.mock('@/modules/auth/use-saved-profiles', () => ({
  useSavedProfiles: (): SavedProfilesMock => ({
    hasProfiles: computed<boolean>(() => get(savedUsernames).length > 0),
    loadProfiles: vi.fn(async () => Promise.resolve()),
    resolveStoredUsername: (): string => get(storedUsername),
    savedUsernames,
  }),
}));

vi.mock('@/modules/auth/login/use-login-remember-options', () => ({
  useLoginRememberOptions: (): RememberOptionsMock => ({
    loadRememberSettings: vi.fn(),
    modelRememberPassword: ref(false),
    modelRememberUsername: ref(false),
    rememberCredentials: vi.fn(async () => Promise.resolve()),
    storedUsername,
  }),
}));

vi.mock('@/modules/auth/login/use-custom-backend', () => ({
  useCustomBackend: (): CustomBackendMock => ({
    clearBackend: vi.fn(),
    display: backendDisplay,
    loadBackendSettings: vi.fn(),
    modelSessionOnly: ref(false),
    modelUrl: backendUrl,
    saveBackend: vi.fn(),
    saved: ref(false),
    serverColor: computed(() => undefined),
    toggleDisplay: vi.fn(),
  }),
}));

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): LogoutMock => ({
    logoutRemoteSession: vi.fn<() => Promise<ActionStatus>>(async () => Promise.resolve({ success: true })),
  }),
}));

const LoginForm = (await import('@/modules/auth/login/LoginForm.vue')).default;

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

const ButtonStub = {
  name: 'RuiButton',
  props: ['disabled', 'loading'],
  template: '<button :disabled="disabled"><slot /></button>',
};

const USERNAME = 'LoginUsernameField';
const PASSWORD = 'password-input';

describe('loginForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof LoginForm>>;

  beforeEach(() => {
    setActivePinia(createPinia());
    set(backendDisplay, false);
    set(backendUrl, '');
    set(savedUsernames, ['saved-user']);
    set(storedUsername, '');
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(props: Record<string, unknown> = {}): VueWrapper<InstanceType<typeof LoginForm>> {
    return mount(LoginForm, {
      global: {
        stubs: {
          ExternalLink: true,
          IncompleteUpgradeAlert: true,
          LoginBackendToggle: true,
          LoginCustomBackendFields: inputStub('LoginCustomBackendFields'),
          LoginRememberOptions: true,
          // The form focuses this one through its template ref on mount.
          LoginUsernameField: { ...inputStub('LoginUsernameField'), methods: { focus: (): void => {} } },
          LoginWelcomeMessageDialog: true,
          PremiumSyncConflictAlert: true,
          RuiButton: ButtonStub,
          RuiRevealableTextField: inputStub('RuiRevealableTextField'),
        },
      },
      props: { loading: false, ...props },
    });
  }

  function usernameField(): VueWrapper<StubInstance> {
    return wrapper.findComponent<StubInstance>({ name: USERNAME });
  }

  function passwordField(): VueWrapper<StubInstance> {
    const match = wrapper.findComponent<StubInstance>(`[data-testid=${PASSWORD}]`);
    assert(match.exists(), 'the password field is not rendered');
    return match;
  }

  function messagesOf(field: VueWrapper<StubInstance>): string[] {
    const value: unknown = field.props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  function submitDisabled(): boolean {
    return wrapper.get('[data-testid=login-submit]').attributes('disabled') !== undefined;
  }

  async function fill(username: string, password: string): Promise<void> {
    usernameField().vm.$emit('update:modelValue', username);
    passwordField().vm.$emit('update:modelValue', password);
    await nextTick();
  }

  async function submit(): Promise<void> {
    await wrapper.get('form').trigger('submit');
    await nextTick();
  }

  function loginPayloads(): LoginCredentials[] {
    const emitted = wrapper.emitted('login') ?? [];
    return emitted.map(([credentials]) => {
      assert(credentials && typeof credentials === 'object');
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the emit is typed at the source; VTU erases it to unknown
      return credentials as LoginCredentials;
    });
  }

  it('should keep submit disabled on an empty form', async () => {
    wrapper = createWrapper();
    await nextTick();

    expect(submitDisabled()).toBe(true);
  });

  it('should enable submit once username and password are filled', async () => {
    wrapper = createWrapper();
    await fill('user', 'password');

    expect(submitDisabled()).toBe(false);
  });

  it('should emit the typed credentials on submit', async () => {
    wrapper = createWrapper();
    await fill('user', 'password');
    await submit();

    expect(loginPayloads()).toStrictEqual([{ password: 'password', username: 'user' }]);
  });

  it.each([
    ['', 'password'],
    ['user', ''],
    ['', ''],
  ])('should keep submit disabled for username %s and password %s', async (username, password) => {
    wrapper = createWrapper();
    await fill(username, password);

    expect(submitDisabled()).toBe(true);
  });

  describe('username rules', () => {
    it.each([
      ['user name'],
      ['user@name'],
      ['user/name'],
    ])('should reject %s', async (username) => {
      wrapper = createWrapper();
      await fill(username, 'password');

      expect(submitDisabled()).toBe(true);
      expect(messagesOf(usernameField())).toStrictEqual(['login.validation.valid_username']);
    });

    it.each([
      ['user_name'],
      ['user.name'],
      ['user-name'],
    ])('should accept %s', async (username) => {
      wrapper = createWrapper();
      await fill(username, 'password');

      expect(submitDisabled()).toBe(false);
      expect(messagesOf(usernameField())).toStrictEqual([]);
    });

    it('should report both messages when cleared after being filled', async () => {
      wrapper = createWrapper();
      await fill('user', 'password');
      await fill('', 'password');

      expect(messagesOf(usernameField())).toStrictEqual([
        'login.validation.valid_username',
        'login.validation.non_empty_username',
      ]);
    });
  });

  describe('password rules', () => {
    it('should show the empty message once cleared', async () => {
      wrapper = createWrapper();
      await fill('user', 'password');
      await fill('user', '');

      expect(messagesOf(passwordField())).toStrictEqual(['login.validation.non_empty_password']);
    });

    // `required` trims, so a password of only spaces is treated as absent.
    it('should reject a whitespace-only password', async () => {
      wrapper = createWrapper();
      await fill('user', '   ');

      expect(submitDisabled()).toBe(true);
      expect(messagesOf(passwordField())).toStrictEqual(['login.validation.non_empty_password']);
    });
  });

  describe('the custom backend panel', () => {
    it('should keep submit disabled while it is open, even on a valid form', async () => {
      wrapper = createWrapper();
      await fill('user', 'password');
      set(backendDisplay, true);
      await nextTick();

      expect(submitDisabled()).toBe(true);
    });

    // The url rules are `$autoDirty`, so an untouched empty field shows nothing at all: the message
    // only appears once a value has been entered and taken away again.
    it('should show nothing on an untouched empty url', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual([]);
    });

    it('should require a url once one has been entered and cleared', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, 'http://rotki.com');
      await nextTick();
      set(backendUrl, '');
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual([
        'login.custom_backend.validation.url',
        'login.custom_backend.validation.non_empty',
      ]);
    });

    it('should reject a malformed url', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, 'not a url');
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual(['login.custom_backend.validation.url']);
    });

    it('should accept a well-formed url', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, 'http://127.0.0.1:4242');
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual([]);
    });

    // Was pinned as rejected while the rule used the shared dotted-host regex, which took
    // `http://127.0.0.1:4242` and refused the name for the same machine. Fixed deliberately.
    it('should accept http://localhost:4242', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, 'http://localhost:4242');
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual([]);
    });

    // The length bound sits in the same rule as the url check, so it reports the same message.
    it('should reject a url of 300 characters or more', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, `http://localhost/${'a'.repeat(300)}`);
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual(['login.custom_backend.validation.url']);
    });

    it('should ignore the url rules while it is closed', async () => {
      wrapper = createWrapper();
      set(backendUrl, 'not a url');
      await fill('user', 'password');

      expect(submitDisabled()).toBe(false);
    });
  });

  // The server errors arrive as a flat string list and are routed to a field by prefix. Both the
  // prefixes and the ordering (local messages first) are contract.
  describe('server errors', () => {
    it('should append a username error to that field', async () => {
      wrapper = createWrapper({ errors: ['User user does not exist'] });
      await nextTick();

      expect(messagesOf(usernameField())).toStrictEqual(['User user does not exist']);
    });

    it('should append a password error to that field', async () => {
      wrapper = createWrapper({ errors: ['Wrong password for user'] });
      await nextTick();

      expect(messagesOf(passwordField())).toStrictEqual(['Wrong password for user']);
    });

    it('should keep the local message first when both are present', async () => {
      wrapper = createWrapper({ errors: ['Wrong password for user'] });
      await fill('user', 'password');
      await fill('user', '');

      expect(messagesOf(passwordField())).toStrictEqual([
        'login.validation.non_empty_password',
        'Wrong password for user',
      ]);
    });

    it('should route an unrecognised error to neither field', async () => {
      wrapper = createWrapper({ errors: ['Something else went wrong'] });
      await nextTick();

      expect(messagesOf(usernameField())).toStrictEqual([]);
      expect(messagesOf(passwordField())).toStrictEqual([]);
    });
  });

  describe('the touched signal', () => {
    it('should emit once the user edits the username', async () => {
      wrapper = createWrapper();
      await fill('user', '');

      expect(wrapper.emitted('touched')).toHaveLength(1);
    });

    // Restoring a remembered username is not a user edit, so it must stay silent.
    it('should stay silent when the username is restored from storage', async () => {
      set(storedUsername, 'saved-user');
      wrapper = createWrapper();
      await nextTick();
      await nextTick();

      expect(wrapper.emitted('touched')).toBeUndefined();
    });
  });

  it('should ask for a new account when no profile is saved', async () => {
    set(savedUsernames, []);
    wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.emitted('new-account')).toHaveLength(1);
  });
});
