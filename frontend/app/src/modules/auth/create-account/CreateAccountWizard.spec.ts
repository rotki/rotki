import type { Component, Ref } from 'vue';
import type { CreateAccountPayload } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import CreateAccountWizard from '@/modules/auth/create-account/CreateAccountWizard.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { hasProfiles, loadProfiles } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { hasProfiles: ref<boolean>(true), loadProfiles: vi.fn(async () => {}) };
});

vi.mock('@/modules/auth/use-saved-profiles', () => ({
  useSavedProfiles: (): { hasProfiles: Ref<boolean>; loadProfiles: Mock } => ({ hasProfiles, loadProfiles }),
}));

/**
 * The later steps stand in as pass-throughs that expose their three outward signals; only the
 * introduction is mounted for real, because the mode choice is the wizard's own first decision.
 */
function stepStub(name: string): Component {
  return {
    emits: ['back', 'next', 'confirm'],
    name,
    props: ['loading', 'mode', 'error'],
    template: `<div :data-testid="'${name}'">
      <button data-testid="stub-back" @click="$emit('back')" />
      <button data-testid="stub-next" @click="$emit('next')" />
      <button data-testid="stub-confirm" @click="$emit('confirm')" />
    </div>`,
  };
}

function createWrapper(props: Record<string, unknown> = {}): VueWrapper<any> {
  return mount(CreateAccountWizard, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        CreateAccountCredentials: stepStub('CreateAccountCredentials'),
        CreateAccountPremium: stepStub('CreateAccountPremium'),
        CreateAccountSubmitStep: stepStub('CreateAccountSubmitStep'),
        // Globally stubbed to `true`, which would swallow the introduction's own copy.
        I18nT: { template: '<div><slot /></div>' },
        RotkiLogo: true,
        // The real tabs render nothing without a measured layout, so every step renders at once.
        RuiTabItem: { template: '<div><slot /></div>' },
        RuiTabItems: { props: ['modelValue'], template: '<div><slot /></div>' },
      },
    },
    props: { loading: false, step: 1, ...props },
  });
}

function lastStep(wrapper: VueWrapper<any>): number | undefined {
  return wrapper.emitted<[number]>('update:step')?.at(-1)?.[0];
}

/**
 * Presses one of a step's three buttons.
 *
 * @remarks
 * Every step renders at once here, so the button is reached through the step's own component
 * rather than the document, where the first step's copy would answer instead.
 */
async function press(wrapper: VueWrapper<any>, step: string, button: string): Promise<void> {
  await wrapper.findComponent({ name: step }).find(`[data-testid=stub-${button}]`).trigger('click');
}

describe('createAccountWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(hasProfiles, true);
  });

  it('should load the saved profiles before it renders', () => {
    createWrapper();

    expect(loadProfiles).toHaveBeenCalledTimes(1);
  });

  describe('the heading', () => {
    it('should offer to create an account by default', () => {
      expect(createWrapper().find('h4').text()).toBe('create_account.title');
    });

    it('should offer to restore one once that mode is chosen', () => {
      const wrapper = createWrapper({ mode: 'restore' });

      expect(wrapper.find('h4').text()).toBe('create_account.title_restore');
    });
  });

  describe('choosing a mode', () => {
    it('should record the choice and move to the next step', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=create-account-introduction-restore]').trigger('click');

      expect(wrapper.emitted<[string]>('update:mode')?.at(-1)?.[0]).toBe('restore');
      expect(lastStep(wrapper)).toBe(2);
    });

    it('should move on for a plain create too', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=create-account-introduction-create]').trigger('click');

      expect(wrapper.emitted<[string]>('update:mode')?.at(-1)?.[0]).toBe('create');
      expect(lastStep(wrapper)).toBe(2);
    });
  });

  describe('stepping back', () => {
    it('should return to the previous step', async () => {
      const wrapper = createWrapper({ mode: 'create', step: 3 });

      await press(wrapper, 'CreateAccountCredentials', 'back');

      expect(lastStep(wrapper)).toBe(2);
    });

    /** The error belongs to the submit the user is stepping away from. */
    it('should clear a submit error on the way back', async () => {
      const wrapper = createWrapper({ error: 'wrong password', mode: 'create', step: 4 });

      await press(wrapper, 'CreateAccountSubmitStep', 'back');

      expect(wrapper.emitted('clear-error')).toHaveLength(1);
    });

    it('should not clear an error that was never raised', async () => {
      const wrapper = createWrapper({ mode: 'create', step: 4 });

      await press(wrapper, 'CreateAccountSubmitStep', 'back');

      expect(wrapper.emitted('clear-error')).toBeUndefined();
    });
  });

  describe('submitting', () => {
    it('should hand the parent the answers collected so far', async () => {
      const wrapper = createWrapper({ mode: 'create', step: 4 });

      await press(wrapper, 'CreateAccountSubmitStep', 'confirm');

      const payload = wrapper.emitted<[CreateAccountPayload]>('confirm')?.[0]?.[0];

      expect(payload).toEqual({
        credentials: { password: '', username: '' },
        initialSettings: { submitUsageAnalytics: true },
      });
    });

    it('should carry the premium setup a restore turned on', async () => {
      const wrapper = createWrapper();
      await wrapper.find('[data-testid=create-account-introduction-restore]').trigger('click');
      await wrapper.setProps({ mode: 'restore', step: 4 });

      await press(wrapper, 'CreateAccountSubmitStep', 'confirm');

      expect(wrapper.emitted<[CreateAccountPayload]>('confirm')?.[0]?.[0].premiumSetup).toEqual({
        apiKey: '',
        apiSecret: '',
        syncDatabase: true,
      });
    });
  });

  describe('the log in shortcut', () => {
    it('should be offered when the machine already has a profile', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=login]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should be withheld when no account has ever been created here', () => {
      set(hasProfiles, false);

      expect(createWrapper().find('[data-testid=login]').exists()).toBe(false);
    });
  });
});
