import type { Ref } from 'vue';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import UserDropdown from '@/modules/shell/components/UserDropdown.vue';
import { createRuiPlugin } from '@/plugins/rui';

const { currentTier, logout, premium, privacyModeIcon, username } = await vi.hoisted(async () => {
  const { ref } = await import('vue');

  return {
    currentTier: ref<string>(''),
    logout: vi.fn<() => Promise<void>>(async () => {}),
    premium: ref<boolean>(false),
    privacyModeIcon: ref<string>('lu-eye'),
    username: ref<string>('alice'),
  };
});

vi.mock('@/modules/auth/use-logout', () => ({
  useLogout: (): { logout: typeof logout } => ({ logout }),
}));

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): { username: Ref<string> } => ({ username }),
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
          props: ['modelValue'],
          template: '<div><slot name="activator" :attrs="{}" /><slot /></div>',
        },
        ThemeControl: true,
      },
    },
  });
}

async function pressLogout(wrapper: VueWrapper<any>): Promise<void> {
  await wrapper.find('[data-testid=logout-button]').trigger('click');
}

describe('userDropdown', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(currentTier, '');
    set(premium, false);
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
    it('should ask in the menu, in place of its items, before doing it', async () => {
      const wrapper = createWrapper();

      await pressLogout(wrapper);

      expect(wrapper.find('[data-testid=inline-confirm]').text()).toContain('user_dropdown.confirmation.message');
      expect(wrapper.find('[data-testid=confirm-menu-entries]').attributes('style')).toContain('display: none');
      expect(logout).not.toHaveBeenCalled();
    });

    it('should log out and forget the saved password once accepted', async () => {
      const wrapper = createWrapper();

      await pressLogout(wrapper);
      await wrapper.find('[data-testid=inline-confirm-accept]').trigger('click');

      expect(logout).toHaveBeenCalledExactlyOnceWith(true, { forgetSavedPassword: true });
    });

    it('should not log out when cancelled, and offer the items again next time', async () => {
      const wrapper = createWrapper();
      wrapper.findComponent({ name: 'RuiMenu' }).vm.$emit('update:modelValue', true);
      await nextTick();

      await pressLogout(wrapper);
      await wrapper.find('[data-testid=inline-confirm-cancel]').trigger('click');

      expect(logout).not.toHaveBeenCalled();
      expect(wrapper.find('[data-testid=inline-confirm]').exists()).toBe(false);
      expect(wrapper.find('[data-testid=logout-button]').exists()).toBe(true);
    });
  });
});
