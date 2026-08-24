import type { LoginCredentials } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, describe, expect, it } from 'vitest';
import { type ComponentPublicInstance, defineComponent, h, ref, type VNode } from 'vue';
import CreateAccountCredentials from '@/modules/auth/create-account/credentials/CreateAccountCredentials.vue';
import '@test/i18n';

/**
 * Guards the step's Continue button, with the REAL form mounted underneath.
 *
 * `CreateAccountCredentialsForm.spec.ts` pins the rules and the `valid` model the form writes; this
 * one pins the other half of that contract - the wizard step actually gating on it. Two regressions
 * live in the gap between them and neither spec alone can see either:
 *
 * - the form stops writing `valid` (the zod swap has no `watchImmediate(v$, ...)` to port), so
 *   Continue never enables and the account wizard dead-locks at this step;
 * - the step binds something truthy-but-not-a-boolean, which is what `form.valid` not unwrapping in
 *   a template produces, so Continue is enabled no matter what the user typed.
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

const ButtonStub = {
  name: 'RuiButton',
  props: ['disabled', 'loading'],
  template: '<button :disabled="disabled"><slot /></button>',
};

const USERNAME = 'create-account-username';
const PASSWORD = 'create-account-password';
const PASSWORD_REPEAT = 'create-account-password-repeat';
const USER_PROMPTED = 'create-account-user-prompted';
const CONTINUE = 'create-account-credentials-continue';

interface State {
  credentials: LoginCredentials;
  passwordConfirm: string;
  userPrompted: boolean;
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

describe('createAccountCredentials', () => {
  let wrapper: VueWrapper;

  afterEach(() => {
    wrapper?.unmount();
  });

  function createWrapper(initial: State = filled(), props: Record<string, unknown> = {}): VueWrapper {
    const form = ref<LoginCredentials>(initial.credentials);
    const passwordConfirm = ref<string>(initial.passwordConfirm);
    const userPrompted = ref<boolean>(initial.userPrompted);

    const parent = defineComponent({
      setup(): () => VNode {
        return () => h(CreateAccountCredentials, {
          'form': get(form),
          'loading': false,
          'onUpdate:form': (value: LoginCredentials): void => set(form, value),
          'onUpdate:passwordConfirm': (value: string): void => set(passwordConfirm, value),
          'onUpdate:userPrompted': (value: boolean): void => set(userPrompted, value),
          'passwordConfirm': get(passwordConfirm),
          'userPrompted': get(userPrompted),
          ...props,
        });
      },
    });

    return mount(parent, {
      global: {
        stubs: {
          RuiButton: ButtonStub,
          RuiCheckbox: inputStub('RuiCheckbox'),
          RuiRevealableTextField: inputStub('RuiRevealableTextField'),
          RuiTextField: inputStub('RuiTextField'),
        },
      },
    });
  }

  function continueDisabled(): boolean {
    return wrapper.get(`[data-testid=${CONTINUE}]`).attributes('disabled') !== undefined;
  }

  async function edit(testId: string, value: string | boolean): Promise<void> {
    // `findComponent(string)` alone types the wrapper as `WrapperLike`, which has no `vm`.
    const field = wrapper.findComponent<StubInstance>(`[data-testid=${testId}]`);
    assert(field.exists(), `no field with test id ${testId} is rendered`);
    field.vm.$emit('update:modelValue', value);
    await nextTick();
  }

  it('should enable continue for a complete set of credentials', async () => {
    wrapper = createWrapper();
    await nextTick();

    expect(continueDisabled()).toBe(false);
  });

  it('should keep continue disabled on a blank step', async () => {
    wrapper = createWrapper(blank());
    await nextTick();

    expect(continueDisabled()).toBe(true);
  });

  it.each([
    [USERNAME, ''],
    [PASSWORD, ''],
    [PASSWORD_REPEAT, ''],
    [USER_PROMPTED, false],
  ] as const)('should disable continue once %s is cleared', async (testId, cleared) => {
    wrapper = createWrapper();
    await edit(testId, cleared);

    expect(continueDisabled()).toBe(true);
  });

  it('should disable continue for an invalid username', async () => {
    wrapper = createWrapper();
    await edit(USERNAME, 'user name');

    expect(continueDisabled()).toBe(true);
  });

  it('should disable continue when the confirmation stops matching', async () => {
    wrapper = createWrapper();
    await edit(PASSWORD_REPEAT, 'different');

    expect(continueDisabled()).toBe(true);
  });

  it('should re-enable continue once the credentials are corrected', async () => {
    wrapper = createWrapper(blank());
    await edit(USERNAME, 'user');
    await edit(PASSWORD, 'password');
    await edit(PASSWORD_REPEAT, 'password');
    await edit(USER_PROMPTED, true);

    expect(continueDisabled()).toBe(false);
  });

  it('should disable continue while the step is loading', async () => {
    wrapper = createWrapper(filled(), { loading: true });
    await nextTick();

    expect(continueDisabled()).toBe(true);
  });

  it('should advance the wizard when continue is pressed', async () => {
    wrapper = createWrapper();
    await nextTick();
    await wrapper.get(`[data-testid=${CONTINUE}]`).trigger('click');

    expect(wrapper.findComponent(CreateAccountCredentials).emitted('next')).toHaveLength(1);
  });
});
