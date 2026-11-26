import type { LoginCredentials } from '@/modules/auth/login';
import type { useCustomBackend } from '@/modules/auth/login/use-custom-backend';
import type { useLoginRememberOptions } from '@/modules/auth/login/use-login-remember-options';
import type { useLogout } from '@/modules/auth/use-logout';
import type { useSavedProfiles } from '@/modules/auth/use-saved-profiles';
import type { ActionStatus } from '@/modules/core/common/action';
import { findStub, type StubInstance } from '@test/utils/component-vm';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { get, set } from '@vueuse/shared';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Component, computed, nextTick, ref } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import '@test/i18n';

const backendDisplay = ref<boolean>(false);
const backendUrl = ref<string>('');
const savedUsernames = ref<string[]>(['saved-user']);
const storedUsername = ref<string>('');
const logoutRemoteSession = vi.fn<() => Promise<ActionStatus>>();
const rememberCredentials = vi.fn<(username: string, password: string) => Promise<void>>();
const rememberPassword = ref<boolean>(false);
const rememberUsername = ref<boolean>(false);
const usernameFocus = vi.fn<() => void>();

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
    modelRememberPassword: rememberPassword,
    modelRememberUsername: rememberUsername,
    rememberCredentials,
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
    logoutRemoteSession,
  }),
}));

const LoginForm = (await import('@/modules/auth/login/LoginForm.vue')).default;

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

/** Renders its title slot, where the form names a failed logout, and emits `action` when asked. */
const AlertStub = {
  emits: ['action'],
  name: 'RuiAlert',
  props: ['actionText', 'type'],
  template: '<div><slot name="title" /><slot /></div>',
};

/** Stands in for both conflict alerts' shared shell, exposing its confirm and cancel buttons. */
const ActionAlertStub = {
  emits: ['confirm', 'cancel'],
  name: 'LoginActionAlert',
  template: `<div data-testid="action-alert">
    <slot name="title" />
    <slot />
    <button data-testid="action-alert-cancel" @click="$emit('cancel')" />
    <button data-testid="action-alert-confirm" @click="$emit('confirm')" />
  </div>`,
};

/** A password field that renders a real input, so focus can land on it. */
const PasswordWithInputStub = {
  ...inputStub('RuiRevealableTextField'),
  template: '<div><input data-testid="password-native-input" /></div>',
};

const USERNAME = 'LoginUsernameField';
const PASSWORD = 'password-input';
const URL_MAX_LENGTH = 300;

describe('loginForm', () => {
  let wrapper: VueWrapper<InstanceType<typeof LoginForm>>;

  beforeEach(() => {
    setActivePinia(createPinia());
    set(backendDisplay, false);
    set(backendUrl, '');
    set(savedUsernames, ['saved-user']);
    set(storedUsername, '');
    logoutRemoteSession.mockReset().mockResolvedValue({ success: true });
    rememberCredentials.mockReset().mockResolvedValue(undefined);
    set(rememberPassword, false);
    set(rememberUsername, false);
    usernameFocus.mockReset();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(
    props: Record<string, unknown> = {},
    options: { stubs?: Record<string, Component | boolean>; attachTo?: HTMLElement } = {},
  ): VueWrapper<InstanceType<typeof LoginForm>> {
    return mount(LoginForm, {
      attachTo: options.attachTo,
      global: {
        stubs: {
          ExternalLink: true,
          IncompleteUpgradeAlert: true,
          LoginBackendToggle: true,
          LoginCustomBackendFields: inputStub('LoginCustomBackendFields'),
          LoginRememberOptions: true,
          LoginUsernameField: { ...inputStub('LoginUsernameField'), methods: { focus: (): void => usernameFocus() } },
          LoginWelcomeMessageDialog: true,
          PremiumSyncConflictAlert: true,
          RuiAlert: AlertStub,
          RuiButton: ButtonStub,
          RuiRevealableTextField: inputStub('RuiRevealableTextField'),
          ...options.stubs,
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

  it('should keep submit disabled on an empty form, exposing no validate() of its own', async () => {
    wrapper = createWrapper();
    await nextTick();

    expect('validate' in wrapper.vm).toBe(false);
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

    it('should accept http://localhost:4242', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, 'http://localhost:4242');
      await nextTick();

      const field = wrapper.findComponent<StubInstance>({ name: 'LoginCustomBackendFields' });
      expect(messagesOf(field)).toStrictEqual([]);
    });

    it('should reject an over-long url with the same message as a malformed one', async () => {
      wrapper = createWrapper();
      set(backendDisplay, true);
      set(backendUrl, `http://localhost/${'a'.repeat(URL_MAX_LENGTH)}`);
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

    it('should keep a username error through the restore from storage, which is not a user edit', async () => {
      set(storedUsername, 'saved-user');
      wrapper = createWrapper({ errors: ['User saved-user does not exist'] });
      await flushPromises();

      expect(usernameField().props('modelValue')).toBe('saved-user');
      expect(messagesOf(usernameField())).toStrictEqual(['User saved-user does not exist']);
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

  describe('logging out the session another client holds', () => {
    const ALREADY_LOGGED_IN = 'User saved-user is already logged in';

    async function logOutOther(): Promise<void> {
      await flushPromises();
      const alert = findStub(wrapper, '[data-testid=login-already-logged-in]');
      assert(alert.exists(), 'the logged-in alert is not rendered');
      expect(alert.props('actionText')).toBe('login.logout');
      alert.vm.$emit('action');
      await flushPromises();
    }

    it('should name a failed logout in the alert that offered it, and not move on', async () => {
      logoutRemoteSession.mockResolvedValue({ message: 'backend unreachable', success: false });
      wrapper = createWrapper({ errors: [ALREADY_LOGGED_IN] });

      await logOutOther();

      expect(wrapper.find('[data-testid=login-logout-failure]').text()).toBe('backend unreachable');
      expect(wrapper.emitted('touched')).toBeUndefined();
    });

    it('should move on once the other session is logged out, naming nothing', async () => {
      wrapper = createWrapper({ errors: [ALREADY_LOGGED_IN] });

      await logOutOther();

      expect(wrapper.emitted('touched')).toHaveLength(1);
      expect(wrapper.find('[data-testid=login-logout-failure]').exists()).toBe(false);
    });

    it('should drop the failure when the next attempt starts', async () => {
      logoutRemoteSession.mockResolvedValueOnce({ message: 'backend unreachable', success: false });
      logoutRemoteSession.mockReturnValueOnce(new Promise<ActionStatus>(() => {}));
      wrapper = createWrapper({ errors: [ALREADY_LOGGED_IN] });

      await logOutOther();
      await logOutOther();

      expect(wrapper.find('[data-testid=login-logout-failure]').exists()).toBe(false);
    });
  });
  describe('remembering credentials', () => {
    it('should hand the submitted username and password to the remember options', async () => {
      set(rememberUsername, true);
      set(rememberPassword, true);
      wrapper = createWrapper();
      await fill('user', 'password');
      await submit();

      expect(rememberCredentials).toHaveBeenCalledTimes(1);
      expect(rememberCredentials).toHaveBeenCalledWith('user', 'password');
    });
  });

  describe('conflicts reported by the backend', () => {
    /** Renders the real conflict alerts, with only their shared shell stubbed. */
    const conflictStubs: Record<string, Component | boolean> = {
      IncompleteUpgradeAlert: false,
      LoginActionAlert: ActionAlertStub,
      PremiumSyncConflictAlert: false,
    };

    async function createWithConflict(
      kind: 'sync' | 'upgrade',
    ): Promise<ReturnType<typeof useSessionAuthStore>> {
      const store = useSessionAuthStore();
      if (kind === 'sync')
        store.syncConflict = { message: 'sync conflict', payload: null };
      else
        store.incompleteUpgradeConflict = { message: 'incomplete upgrade' };

      wrapper = createWrapper({}, { stubs: conflictStubs });
      await fill('user', 'password');
      return store;
    }

    async function click(testId: string): Promise<void> {
      const alerts = wrapper.findAll('[data-testid=action-alert]');
      expect(alerts).toHaveLength(1);
      await wrapper.get(`[data-testid=${testId}]`).trigger('click');
      await flushPromises();
    }

    it('should keep submit disabled while a conflict is pending', async () => {
      await createWithConflict('sync');

      expect(submitDisabled()).toBe(true);
    });

    it.each([
      ['action-alert-confirm', 'yes'],
      ['action-alert-cancel', 'no'],
    ] as const)('should log in with the sync approval when %s is clicked', async (button, approval) => {
      await createWithConflict('sync');
      await click(button);

      expect(loginPayloads()).toStrictEqual([{ password: 'password', syncApproval: approval, username: 'user' }]);
      expect(rememberCredentials).toHaveBeenCalledWith('user', 'password');
    });

    it('should log in resuming from the backup when the upgrade is resumed', async () => {
      await createWithConflict('upgrade');
      await click('action-alert-confirm');

      expect(loginPayloads()).toStrictEqual([{ password: 'password', resumeFromBackup: true, username: 'user' }]);
      expect(rememberCredentials).toHaveBeenCalledWith('user', 'password');
    });

    it('should clear both conflicts without logging in when the upgrade is aborted', async () => {
      const store = await createWithConflict('upgrade');
      store.syncConflict = { message: 'sync conflict', payload: null };
      await nextTick();
      await wrapper.findComponent({ name: 'IncompleteUpgradeAlert' }).get('[data-testid=action-alert-cancel]').trigger('click');
      await flushPromises();

      expect(wrapper.emitted('login')).toBeUndefined();
      expect(store.syncConflict).toBeUndefined();
      expect(store.incompleteUpgradeConflict).toBeUndefined();
      expect(wrapper.find('[data-testid=action-alert]').exists()).toBe(false);
      expect(submitDisabled()).toBe(false);
    });
  });

  describe('initial focus', () => {
    /**
     * Pins today's timing, not the intent: the focus is picked on mount, a tick before the awaited
     * profile load restores the username, so the password branch never wins at mount.
     */
    it('should focus the username field at mount even when a username is then restored', async () => {
      set(storedUsername, 'saved-user');
      wrapper = createWrapper({}, { attachTo: document.body, stubs: { RuiRevealableTextField: PasswordWithInputStub } });
      await flushPromises();

      expect(usernameField().props('modelValue')).toBe('saved-user');
      expect(usernameFocus).toHaveBeenCalledTimes(1);
      expect(document.activeElement).not.toBe(wrapper.get('[data-testid=password-native-input]').element);
    });

    it('should focus the username field when nothing is restored', async () => {
      wrapper = createWrapper({}, { attachTo: document.body, stubs: { RuiRevealableTextField: PasswordWithInputStub } });
      await flushPromises();

      expect(usernameFocus).toHaveBeenCalledTimes(1);
      expect(document.activeElement).not.toBe(wrapper.get('[data-testid=password-native-input]').element);
    });
  });
});
