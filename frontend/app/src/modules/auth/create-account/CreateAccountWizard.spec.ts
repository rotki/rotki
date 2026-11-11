import type { Component, Ref } from 'vue';
import type { CreateAccountMode } from '@/modules/auth/create-account/types';
import type { CreateAccountPayload } from '@/modules/auth/login';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import CreateAccountWizard from '@/modules/auth/create-account/CreateAccountWizard.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { hasProfiles, loadProfiles } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { hasProfiles: ref<boolean>(true), loadProfiles: vi.fn(async () => {}) };
});

vi.mock('@/modules/auth/use-saved-profiles', () => ({
  useSavedProfiles: (): { hasProfiles: Ref<boolean>; loadProfiles: Mock } => ({ hasProfiles, loadProfiles }),
}));

/** The steps stand in as buttons for their outward signals; the wizard's own job is the routing between them. */
function stepStub(name: string): Component {
  return {
    emits: ['back', 'next', 'confirm', 'go-to'],
    name,
    props: ['loading', 'mode', 'error', 'apiKey', 'username'],
    template: `<div data-testid="${name}">
      <button data-testid="stub-back" @click="$emit('back')" />
      <button data-testid="stub-next" @click="$emit('next')" />
      <button data-testid="stub-confirm" @click="$emit('confirm')" />
      <button data-testid="stub-go-to" @click="$emit('go-to', 'premium')" />
    </div>`,
  };
}

const STEPS = ['CreateAccountPremium', 'CreateAccountCredentials', 'CreateAccountPreferences', 'CreateAccountRestoreSummary'];

function createWrapper(props: { mode?: CreateAccountMode; step?: number; error?: string } = {}): VueWrapper {
  return mount(CreateAccountWizard, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        ...Object.fromEntries(STEPS.map(name => [name, stepStub(name)])),
        I18nT: { template: '<div><slot /></div>' },
      },
    },
    props: { loading: false, step: 1, ...props },
  });
}

/** The parent page owns step and mode, so the wizard's v-model writes are fed back like it would. */
async function follow(wrapper: VueWrapper): Promise<void> {
  const step = wrapper.emitted<[number]>('update:step')?.at(-1)?.[0];
  const mode = wrapper.emitted<[CreateAccountMode | undefined]>('update:mode');
  await wrapper.setProps({
    ...(step === undefined ? {} : { step }),
    ...(mode ? { mode: mode.at(-1)?.[0] } : {}),
  });
}

function shownStep(wrapper: VueWrapper): string | undefined {
  return STEPS.find(name => wrapper.find(`[data-testid=${name}]`).exists());
}

async function press(wrapper: VueWrapper, button: string): Promise<void> {
  await wrapper.find(`[data-testid=stub-${button}]`).trigger('click');
  await follow(wrapper);
}

function payload(wrapper: VueWrapper): CreateAccountPayload | undefined {
  return wrapper.emitted<[CreateAccountPayload]>('confirm')?.[0]?.[0];
}

describe('createAccountWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('en-US');
    set(hasProfiles, true);
  });

  it('should load the saved profiles before it renders', () => {
    createWrapper();

    expect(loadProfiles).toHaveBeenCalledTimes(1);
  });

  describe('the path choice', () => {
    it('should come first, with no step counter', () => {
      const wrapper = createWrapper();

      expect(wrapper.find('[data-testid=create-account-heading]').text()).toBe('create_account.entry.title');
      expect(wrapper.find('[data-testid=create-account-step-progress]').exists()).toBe(false);
      expect(shownStep(wrapper)).toBeUndefined();
    });

    it('should start a create on its profile step', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=create-account-introduction-create]').trigger('click');
      await follow(wrapper);

      expect(shownStep(wrapper)).toBe('CreateAccountCredentials');
      expect(wrapper.find('[data-testid=create-account-step-progress]').text()).toContain('create_account.step_progress');
    });

    it('should start a restore on its premium step', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=create-account-introduction-restore]').trigger('click');
      await follow(wrapper);

      expect(shownStep(wrapper)).toBe('CreateAccountPremium');
    });
  });

  describe('the steps of each path', () => {
    it.each([
      ['create', 1, 'CreateAccountCredentials'],
      ['create', 2, 'CreateAccountPreferences'],
      ['restore', 1, 'CreateAccountPremium'],
      ['restore', 2, 'CreateAccountCredentials'],
      ['restore', 3, 'CreateAccountRestoreSummary'],
    ] as const)('should show the %s path\'s step %i as %s', (mode, step, expected) => {
      expect(shownStep(createWrapper({ mode, step }))).toBe(expected);
    });

    it('should title the heading after the step on show', () => {
      expect(createWrapper({ mode: 'restore', step: 3 }).find('[data-testid=create-account-heading]').text())
        .toBe('create_account.steps.summary.title');
    });
  });

  describe('moving through a restore', () => {
    it('should walk forward from premium to the summary', async () => {
      const wrapper = createWrapper({ mode: 'restore', step: 1 });

      await press(wrapper, 'next');
      await press(wrapper, 'next');

      expect(shownStep(wrapper)).toBe('CreateAccountRestoreSummary');
    });

    it('should jump from the summary to the step being changed', async () => {
      const wrapper = createWrapper({ mode: 'restore', step: 3 });

      await press(wrapper, 'go-to');

      expect(shownStep(wrapper)).toBe('CreateAccountPremium');
    });
  });

  describe('stepping back', () => {
    it('should return to the previous step', async () => {
      const wrapper = createWrapper({ mode: 'create', step: 2 });

      await press(wrapper, 'back');

      expect(shownStep(wrapper)).toBe('CreateAccountCredentials');
    });

    it('should return to the path choice from the first step', async () => {
      const wrapper = createWrapper({ mode: 'create', step: 1 });

      await press(wrapper, 'back');

      expect(shownStep(wrapper)).toBeUndefined();
      expect(wrapper.find('[data-testid=create-account-introduction-create]').exists()).toBe(true);
    });

    /** The error belongs to the submit the user is stepping away from. */
    it('should clear a submit error on the way back', async () => {
      const wrapper = createWrapper({ error: 'wrong password', mode: 'create', step: 2 });

      await press(wrapper, 'back');

      expect(wrapper.emitted('clear-error')).toHaveLength(1);
    });

    it('should clear a submit error when jumping back from the summary', async () => {
      const wrapper = createWrapper({ error: 'device limit', mode: 'restore', step: 3 });

      await press(wrapper, 'go-to');

      expect(wrapper.emitted('clear-error')).toHaveLength(1);
    });

    it('should not clear an error that was never raised', async () => {
      const wrapper = createWrapper({ mode: 'create', step: 2 });

      await press(wrapper, 'back');

      expect(wrapper.emitted('clear-error')).toBeUndefined();
    });
  });

  describe('submitting', () => {
    it('should hand the parent a create built from the answers', async () => {
      const wrapper = createWrapper();
      await wrapper.find('[data-testid=create-account-introduction-create]').trigger('click');
      await follow(wrapper);
      await press(wrapper, 'next');

      await press(wrapper, 'confirm');

      expect(payload(wrapper)).toStrictEqual({
        credentials: { password: '', username: '' },
        initialSettings: { mainCurrency: 'USD', submitUsageAnalytics: true },
      });
    });

    it('should hand the parent a restore that downloads the database', async () => {
      const wrapper = createWrapper();
      await wrapper.find('[data-testid=create-account-introduction-restore]').trigger('click');
      await follow(wrapper);
      await press(wrapper, 'next');
      await press(wrapper, 'next');

      await press(wrapper, 'confirm');

      expect(payload(wrapper)?.premiumSetup).toStrictEqual({ apiKey: '', apiSecret: '', syncDatabase: true });
    });
  });

  describe('moving focus', () => {
    /** The button that moved the user on leaves with its step, which would drop focus to the page. */
    it('should give the new step\'s heading the focus', async () => {
      const wrapper = mount(CreateAccountWizard, {
        attachTo: document.body,
        global: {
          plugins: [createRuiPlugin({})],
          stubs: {
            ...Object.fromEntries(STEPS.map(name => [name, stepStub(name)])),
            I18nT: { template: '<div><slot /></div>' },
            transition: false,
          },
        },
        props: { loading: false, mode: 'restore', step: 1 },
      });
      const next = wrapper.find('[data-testid=stub-next]');
      assert(next.element instanceof HTMLElement);
      next.element.focus();

      await next.trigger('click');
      await follow(wrapper);
      await vi.waitFor(() => {
        expect(document.activeElement?.getAttribute('data-testid')).toBe('create-account-heading');
      });

      expect(document.activeElement?.textContent?.trim()).toBe('create_account.steps.profile.restore_title');
    });
  });

  describe('the log in shortcut', () => {
    it('should be offered when the machine already has a profile', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=login]').trigger('click');

      expect(wrapper.emitted('cancel')).toHaveLength(1);
    });

    it('should be withheld when no profile has ever been created here', () => {
      set(hasProfiles, false);

      expect(createWrapper().find('[data-testid=login]').exists()).toBe(false);
    });

    it('should leave the path choice with the choice', () => {
      expect(createWrapper({ mode: 'create', step: 1 }).find('[data-testid=login]').exists()).toBe(false);
    });
  });
});
