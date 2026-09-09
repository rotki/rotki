import type { Ref } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, type Mock, vi } from 'vitest';
import UserDropdown from '@/modules/shell/components/UserDropdown.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { confirm, currentTier, interop, logout, premium, privacyModeIcon, savedRememberPassword, username } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  /** Holds the callback the confirmation store was handed, so a test can accept the prompt. */
  const confirm: { run?: () => Promise<void> } = {};

  return {
    confirm,
    currentTier: ref<string>(''),
    interop: { clearPassword: vi.fn(), isPackaged: false },
    logout: vi.fn(),
    premium: ref<boolean>(false),
    privacyModeIcon: ref<string>('lu-eye'),
    savedRememberPassword: ref<boolean>(false),
    username: ref<string>('alice'),
  };
});

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): { logout: Mock } => ({ logout }),
}));

vi.mock('@/modules/auth/use-remember-settings', () => ({
  useRememberSettings: (): { savedRememberPassword: Ref<boolean> } => ({ savedRememberPassword }),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): { username: Ref<string> } => ({ username }),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): typeof interop => interop,
}));

vi.mock('@/modules/premium/use-premium-helper', () => ({
  usePremiumHelper: (): { currentTier: Ref<string>; premium: Ref<boolean> } => ({ currentTier, premium }),
}));

vi.mock('@/modules/settings/use-privacy', () => ({
  usePrivacyMode: (): Record<string, unknown> => ({
    privacyModeIcon,
    togglePrivacyMode: vi.fn(),
  }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): { show: (message: unknown, run: () => Promise<void>) => void } => ({
    show: (_message, run): void => {
      confirm.run = run;
    },
  }),
}));

function createWrapper(): VueWrapper<any> {
  return mount(UserDropdown, {
    global: {
      plugins: [createRuiPlugin({})],
      stubs: {
        // An auto-stub renders no default slot, which would hide the tier label it wraps.
        ExternalLink: { name: 'ExternalLink', props: ['url', 'custom'], template: '<div><slot /></div>' },
        MenuTooltipButton: { name: 'MenuTooltipButton', template: '<button><slot /></button>' },
        // Both slots are scoped, so the stubs have to hand back what the template destructures.
        RouterLink: { name: 'RouterLink', template: '<div><slot :navigate="() => {}" /></div>' },
        RuiMenu: {
          name: 'RuiMenu',
          template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
        },
        ThemeControl: true,
      },
    },
  });
}

/** Presses log out and accepts the confirmation. */
async function logOut(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-testid=logout-button]').trigger('click');
  await confirm.run?.();
}

describe('userDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    confirm.run = undefined;
    interop.isPackaged = false;
    set(currentTier, '');
    set(premium, false);
    set(savedRememberPassword, false);
    set(username, 'alice');
  });

  it('should name the signed in account', () => {
    expect(createWrapper().find('[data-testid=username]').text()).toContain('alice');
  });

  describe('the premium tier', () => {
    it('should be named for a premium account', () => {
      set(premium, true);
      set(currentTier, 'Pro');

      expect(createWrapper().text()).toContain('premium_placeholder.current_plan::Pro');
    });

    it('should be left out for a non-premium account', () => {
      set(currentTier, 'Pro');

      expect(createWrapper().text()).not.toContain('premium_placeholder.current_plan');
    });

    it('should be left out when premium reports no tier', () => {
      set(premium, true);

      expect(createWrapper().text()).not.toContain('premium_placeholder.current_plan');
    });
  });

  describe('logging out', () => {
    it('should ask before doing it', async () => {
      const wrapper = createWrapper();

      await wrapper.find('[data-testid=logout-button]').trigger('click');

      expect(logout).not.toHaveBeenCalled();
    });

    it('should log out once confirmed', async () => {
      const wrapper = createWrapper();

      await logOut(wrapper);

      expect(logout).toHaveBeenCalledTimes(1);
    });

    /**
     * Only the packaged build stores the password, and only when the user asked it to. Clearing it
     * on log out is what stops the next person on the machine signing straight back in.
     */
    it('should clear a password the desktop build remembered', async () => {
      interop.isPackaged = true;
      set(savedRememberPassword, true);

      await logOut(createWrapper());

      expect(interop.clearPassword).toHaveBeenCalledTimes(1);
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('should clear nothing when the password was never remembered', async () => {
      interop.isPackaged = true;

      await logOut(createWrapper());

      expect(interop.clearPassword).not.toHaveBeenCalled();
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('should clear nothing in a browser, which stores no password', async () => {
      set(savedRememberPassword, true);

      await logOut(createWrapper());

      expect(interop.clearPassword).not.toHaveBeenCalled();
      expect(logout).toHaveBeenCalledTimes(1);
    });
  });
});
