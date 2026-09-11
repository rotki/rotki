import type { Pinia } from 'pinia';
import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CreateAccountWizard from '@/modules/auth/create-account/CreateAccountWizard.vue';
import CreateAccountPage from './index.vue';

// The seam: the page owns the shared unlock flow's error state for the create screen. It must
// clear a terminal error on mount (the flow is a singleton that survives the login -> create
// navigation) and on the wizard's `clear-error`, and forward `confirm`/`cancel` unchanged.
const { clearErrors, createNewAccount, errorRef, loadingRef, navigateToUserLogin } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    clearErrors: vi.fn(),
    createNewAccount: vi.fn().mockResolvedValue(undefined),
    errorRef: vueRef(''),
    loadingRef: vueRef(false),
    navigateToUserLogin: vi.fn(),
  };
});

vi.mock('@/modules/auth/use-account-management', () => ({
  useAccountManagement: vi.fn(() => ({ clearErrors, createNewAccount, error: errorRef, loading: loadingRef })),
}));

vi.mock('@/modules/shell/layout/use-navigation', () => ({
  useAppNavigation: vi.fn(() => ({ navigateToUserLogin })),
}));

function mountPage(pinia: Pinia): VueWrapper {
  // UserHost wraps the wizard in its default slot; render the slot so the child is mounted
  // (as a shallow stub) and findable.
  return shallowMount(CreateAccountPage, {
    global: { plugins: [pinia], stubs: { UserHost: { template: '<div><slot /></div>' } } },
  });
}

describe('pages/user/create', () => {
  let pinia: Pinia;
  let wrapper: VueWrapper | undefined;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    set(errorRef, '');
    set(loadingRef, false);
  });

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  it('should clear a terminal error on mount, so a failed login does not leak in', () => {
    wrapper = mountPage(pinia);
    expect(clearErrors).toHaveBeenCalledTimes(1);
  });

  it('should pass the flow error down to the wizard', async () => {
    wrapper = mountPage(pinia);
    set(errorRef, 'Wrong password or invalid/corrupt database for user');
    await nextTick();
    expect(wrapper.findComponent(CreateAccountWizard).props('error')).toBe(
      'Wrong password or invalid/corrupt database for user',
    );
  });

  it('should clear the flow error when the wizard dismisses it', async () => {
    wrapper = mountPage(pinia);
    // `error` is a read-only projection of the flow state, so the page must go through
    // `clearErrors()`; assigning to it silently did nothing.
    wrapper.findComponent(CreateAccountWizard).vm.$emit('clear-error');
    await nextTick();
    expect(clearErrors).toHaveBeenCalledTimes(2);
  });

  it('should delegate to createNewAccount on confirm', async () => {
    wrapper = mountPage(pinia);
    const payload = { credentials: { password: 'p', username: 'alice' } };
    wrapper.findComponent(CreateAccountWizard).vm.$emit('confirm', payload);
    await nextTick();
    expect(createNewAccount).toHaveBeenCalledWith(payload);
  });

  it('should navigate back to the login page on cancel', async () => {
    wrapper = mountPage(pinia);
    wrapper.findComponent(CreateAccountWizard).vm.$emit('cancel');
    await nextTick();
    expect(navigateToUserLogin).toHaveBeenCalled();
  });
});
