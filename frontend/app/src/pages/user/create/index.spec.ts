import type { Pinia } from 'pinia';
import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CreateAccountWizard from '@/modules/auth/create-account/CreateAccountWizard.vue';
import CreateAccountPage from './index.vue';

const { clearErrors, createNewAccount, errorRef, loadingRef, navigateToUserLogin } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    clearErrors: vi.fn(),
    createNewAccount: vi.fn().mockResolvedValue(undefined),
    errorRef: ref<string>(''),
    loadingRef: ref<boolean>(false),
    navigateToUserLogin: vi.fn(),
  };
});

vi.mock('@/modules/auth/use-account-management', () => ({
  useAccountManagement: vi.fn(() => ({ clearErrors, createNewAccount, error: errorRef, loading: loadingRef })),
}));

vi.mock('@/modules/shell/layout/use-navigation', () => ({
  useAppNavigation: vi.fn(() => ({ navigateToUserLogin })),
}));

const UserHostSlotStub = { template: '<div><slot /></div>' };

function mountPage(pinia: Pinia): VueWrapper {
  return shallowMount(CreateAccountPage, {
    global: { plugins: [pinia], stubs: { UserHost: UserHostSlotStub } },
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

  it('should clear the unlock flow error on mount, since the flow outlives a failed login', () => {
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

  it('should clear the read-only flow error through clearErrors when the wizard dismisses it', async () => {
    wrapper = mountPage(pinia);
    clearErrors.mockClear();
    wrapper.findComponent(CreateAccountWizard).vm.$emit('clear-error');
    await nextTick();
    expect(clearErrors).toHaveBeenCalledTimes(1);
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
