import type { StubInstance } from '@test/utils/component-vm';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, ref, type VNode } from 'vue';
import PasswordConfirmationDialog from '@/modules/auth/login/PasswordConfirmationDialog.vue';
import '@test/i18n';

const getPassword = vi.fn<(username: string) => Promise<string>>();

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { getPassword: typeof getPassword } => ({ getPassword }),
}));

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
  confirmed: () => string[];
  display: () => boolean;
  setDisplay: (value: boolean) => void;
}

describe('passwordConfirmationDialog', () => {
  let harness: Harness;

  beforeEach(() => {
    getPassword.mockReset();
    getPassword.mockResolvedValue('');
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

  it('should confirm again after a rejected attempt', async () => {
    harness = createHarness();
    await type('wrong');
    await confirm();
    await type('right');
    await confirm();

    expect(harness.confirmed()).toStrictEqual(['wrong', 'right']);
  });

  describe('when the backend has reported an error', () => {
    it('should show that error alongside the local message', async () => {
      harness = createHarness({ errorMessage: 'Wrong password' });
      await confirm();

      expect(messages()).toStrictEqual([
        'password_confirmation_dialog.validation.non_empty_password',
        'Wrong password',
      ]);
    });

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

    it('should drop that error once the password is edited', async () => {
      harness = createHarness({ errorMessage: 'Wrong password' });
      await nextTick();
      expect(messages()).toStrictEqual(['Wrong password']);

      await type('another');

      expect(messages()).toStrictEqual([]);
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
