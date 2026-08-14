import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ComponentPublicInstance, defineComponent, h, ref, type VNode } from 'vue';
import PasswordConfirmationDialog from '@/modules/auth/login/PasswordConfirmationDialog.vue';
import '@test/i18n';

/**
 * Characterization of the vuelidate rules, written before the zod migration.
 *
 * This dialog had no coverage of any kind - no unit spec, no e2e - and it guards the password
 * re-entry that unlocks a session, so the contract is pinned before anything moves.
 *
 * The seam is what the dialog exposes to `AppMessages.vue`: the `confirm` emit carrying the typed
 * password, the `display` model, and the `error-messages` the input receives. No markup assertions.
 *
 * NOT covered: the `@keydown.enter` submit path. The listener falls through onto the stubbed input,
 * where neither `trigger('keydown.enter')` nor a real dispatched `KeyboardEvent` reaches it, so the
 * only test that could be written for it is one that cannot fail. It runs the same
 * `confirmPassword()` as the button, so the validation contract below still covers the logic - but
 * the binding itself is unpinned and stays that way through the migration.
 */

const getPassword = vi.fn<(username: string) => Promise<string>>();

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { getPassword: typeof getPassword } => ({ getPassword }),
}));

/** The stub declares its props at runtime, so its instance is typed loosely. */
type StubInstance = ComponentPublicInstance<Record<string, unknown>>;

const TextFieldStub = {
  emits: ['update:modelValue'],
  name: 'RuiTextField',
  props: ['modelValue', 'errorMessages', 'disabled'],
  template: '<div />',
};

const PassthroughStub = {
  name: 'Passthrough',
  template: '<div><slot name="header" /><slot /><slot name="footer" /></div>',
};

interface Harness {
  wrapper: VueWrapper;
  /** Passwords the dialog has confirmed, in order. */
  confirmed: () => string[];
  /** The dialog's own visibility model. */
  display: () => boolean;
  setDisplay: (value: boolean) => void;
}

describe('passwordConfirmationDialog', () => {
  let harness: Harness;

  beforeEach(() => {
    getPassword.mockReset();
    getPassword.mockResolvedValue('');
  });

  afterEach(() => {
    harness?.wrapper.unmount();
  });

  function createHarness(props: { username?: string; errorMessage?: string } = {}): Harness {
    const display = ref<boolean>(true);
    const confirmed = ref<string[]>([]);

    const parent = defineComponent({
      setup(): () => VNode {
        return () => h(PasswordConfirmationDialog, {
          'modelValue': get(display),
          'onConfirm': (password: string): void => {
            set(confirmed, [...get(confirmed), password]);
          },
          'onUpdate:modelValue': (value: boolean): void => set(display, value),
          'username': 'user',
          ...props,
        });
      },
    });

    const wrapper = mount(parent, {
      global: {
        stubs: {
          RuiButton: PassthroughStub,
          RuiCard: PassthroughStub,
          RuiDialog: PassthroughStub,
          RuiTextField: TextFieldStub,
        },
      },
    });

    return {
      confirmed: (): string[] => get(confirmed),
      display: (): boolean => get(display),
      setDisplay: (value: boolean): void => set(display, value),
      wrapper,
    };
  }

  function input(): VueWrapper<StubInstance> {
    const match = harness.wrapper.findComponent<StubInstance>('[data-testid=password-confirmation-input]');
    assert(match.exists(), 'the password input is not rendered');
    return match;
  }

  function messages(): string[] {
    const value: unknown = input().props('errorMessages');
    assert(Array.isArray(value));
    return value.map(String);
  }

  async function type(password: string): Promise<void> {
    input().vm.$emit('update:modelValue', password);
    await nextTick();
  }

  async function confirm(): Promise<void> {
    await harness.wrapper.get('[data-testid=password-confirmation-confirm]').trigger('click');
    await nextTick();
  }

  it('should confirm with the typed password', async () => {
    harness = createHarness();
    await type('secret');
    await confirm();

    expect(harness.confirmed()).toStrictEqual(['secret']);
  });

  it('should not confirm while the password is empty', async () => {
    harness = createHarness();
    await confirm();

    expect(harness.confirmed()).toStrictEqual([]);
  });

  it('should show the empty-password message once confirm is attempted', async () => {
    harness = createHarness();
    await confirm();

    expect(messages()).toStrictEqual(['password_confirmation_dialog.validation.non_empty_password']);
  });

  it('should show no message before the user has done anything', async () => {
    harness = createHarness();
    await nextTick();

    expect(messages()).toStrictEqual([]);
  });

  // Vuelidate's `required` trims, so a password of only spaces never reaches the backend.
  it('should not confirm a whitespace-only password', async () => {
    harness = createHarness();
    await type('   ');
    await confirm();

    expect(harness.confirmed()).toStrictEqual([]);
    expect(messages()).toStrictEqual(['password_confirmation_dialog.validation.non_empty_password']);
  });

  it('should clear a shown message once a password is typed', async () => {
    harness = createHarness();
    await confirm();
    expect(messages()).not.toStrictEqual([]);

    await type('secret');

    expect(messages()).toStrictEqual([]);
  });

  // The dialog stays mounted across a rejected attempt, so a second submission must be possible.
  it('should confirm again after a rejected attempt', async () => {
    harness = createHarness();
    await type('wrong');
    await confirm();
    await type('right');
    await confirm();

    expect(harness.confirmed()).toStrictEqual(['wrong', 'right']);
  });

  describe('when the backend has reported an error', () => {
    it('should show that error instead of the local message', async () => {
      harness = createHarness({ errorMessage: 'Wrong password' });
      await confirm();

      expect(messages()).toStrictEqual(['Wrong password']);
    });

    // The server error wins unconditionally, so it keeps showing over an untouched empty field.
    it('should show that error even before the user types', async () => {
      harness = createHarness({ errorMessage: 'Wrong password' });
      await nextTick();

      expect(messages()).toStrictEqual(['Wrong password']);
    });

    it('should still refuse to confirm an empty password', async () => {
      harness = createHarness({ errorMessage: 'Wrong password' });
      await confirm();

      expect(harness.confirmed()).toStrictEqual([]);
    });
  });

  describe('when the dialog is reopened', () => {
    it('should clear the previously typed password', async () => {
      harness = createHarness();
      await type('secret');

      harness.setDisplay(false);
      await nextTick();
      harness.setDisplay(true);
      await nextTick();

      expect(input().props('modelValue')).toBe('');
    });

    it('should clear a message left over from the previous attempt', async () => {
      harness = createHarness();
      await confirm();
      expect(messages()).not.toStrictEqual([]);

      harness.setDisplay(false);
      await nextTick();
      harness.setDisplay(true);
      await nextTick();

      expect(messages()).toStrictEqual([]);
    });
  });
});
