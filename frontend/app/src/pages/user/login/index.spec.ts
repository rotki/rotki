import type { Pinia } from 'pinia';
import { createCustomPinia } from '@test/utils/create-pinia';
import { shallowMount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import LoginForm from '@/modules/auth/login/LoginForm.vue';
import LoginUnlockStage from '@/modules/auth/unlock-flow/LoginUnlockStage.vue';
import { UnlockPhase } from '@/modules/auth/unlock-flow/use-unlock-flow';
import LoginPage from './index.vue';

const { applyUpdate, clearErrors, errorsRef, loadingRef, performInitialChecks, reset, skipUpdate, stateRef, upgradeVisibleRef, userLogin } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    applyUpdate: vi.fn().mockResolvedValue(undefined),
    clearErrors: vi.fn(),
    errorsRef: vueRef([]),
    loadingRef: vueRef(false),
    performInitialChecks: vi.fn().mockResolvedValue(undefined),
    reset: vi.fn(),
    skipUpdate: vi.fn().mockResolvedValue(undefined),
    stateRef: vueRef({ kind: 'idle' }),
    upgradeVisibleRef: vueRef(false),
    userLogin: vi.fn().mockResolvedValue(undefined),
  };
});

vi.mock('@/modules/auth/use-account-management', () => ({
  useAccountManagement: vi.fn(() => ({ clearErrors, errors: errorsRef, loading: loadingRef, userLogin })),
}));

vi.mock('@/modules/auth/unlock-flow/use-unlock-flow-controller', () => ({
  useUnlockFlowController: vi.fn(() => ({ applyUpdate, reset, skipUpdate, state: stateRef, upgradeVisible: upgradeVisibleRef })),
}));

vi.mock('@/pages/user/login/use-login-initial-checks', () => ({
  useLoginInitialChecks: vi.fn(() => ({ performInitialChecks })),
}));

vi.mock('@/modules/core/messaging/use-dynamic-messages', () => ({
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  useDynamicMessages: vi.fn(() => ({ activeWelcomeMessages: require('vue').ref([]), fetchMessages: vi.fn(), welcomeHeader: require('vue').ref(undefined), welcomeMessage: require('vue').ref(undefined) })),
}));

vi.mock('@/modules/core/messaging/use-update-message', () => ({
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  useUpdateMessage: vi.fn(() => ({ showReleaseNotes: require('vue').ref(false) })),
}));

vi.mock('@/modules/shell/app/use-backend-management', () => ({
  useBackendManagement: vi.fn(() => ({ backendChanged: vi.fn() })),
}));

vi.mock('@/modules/shell/layout/use-navigation', () => ({
  useAppNavigation: vi.fn(() => ({ navigateToUserCreation: vi.fn() })),
}));

function mountPage(pinia: Pinia): VueWrapper {
  // UserHost wraps the form/stage in its default slot; render the slot so the children
  // are mounted (as shallow stubs) and findable.
  return shallowMount(LoginPage, {
    global: { plugins: [pinia], stubs: { UserHost: { template: '<div><slot /></div>' } } },
  });
}

describe('pages/user/login', () => {
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    vi.clearAllMocks();
    set(stateRef, { kind: UnlockPhase.idle });
  });

  it('should show the login form on the idle phase', () => {
    const wrapper = mountPage(pinia);
    expect(wrapper.findComponent(LoginForm).exists()).toBe(true);
    expect(wrapper.findComponent(LoginUnlockStage).exists()).toBe(false);
  });

  it('should reset the shared flow on mount (so a post-logout terminal state is cleared)', () => {
    mountPage(pinia);
    expect(reset).toHaveBeenCalled();
  });

  it('should show the login form on the error phase (so its alerts render)', async () => {
    const wrapper = mountPage(pinia);
    set(stateRef, { error: { kind: 'unknown', message: 'x' }, kind: UnlockPhase.error });
    await nextTick();
    expect(wrapper.findComponent(LoginForm).exists()).toBe(true);
  });

  it('should switch to the unlock stage for the asset-update phase', async () => {
    const wrapper = mountPage(pinia);
    set(stateRef, { changes: { changes: 1, local: 1, remote: 2, upToVersion: 2 }, kind: UnlockPhase.updatePrompt });
    await nextTick();
    expect(wrapper.findComponent(LoginForm).exists()).toBe(false);
    expect(wrapper.findComponent(LoginUnlockStage).exists()).toBe(true);
  });

  it('should keep the login form mounted through a plain unlock (so a wrong-password error survives)', async () => {
    const wrapper = mountPage(pinia);
    set(stateRef, { kind: UnlockPhase.unlocking });
    await nextTick();
    expect(wrapper.findComponent(LoginForm).exists()).toBe(true);
    expect(wrapper.findComponent(LoginUnlockStage).exists()).toBe(false);
  });

  it('should show the unlock stage while a DB upgrade runs during unlock', async () => {
    const wrapper = mountPage(pinia);
    set(upgradeVisibleRef, true);
    set(stateRef, { kind: UnlockPhase.unlocking });
    await nextTick();
    expect(wrapper.findComponent(LoginForm).exists()).toBe(false);
    expect(wrapper.findComponent(LoginUnlockStage).exists()).toBe(true);
  });

  it('should clear errors and delegate to userLogin on submit', async () => {
    const wrapper = mountPage(pinia);
    wrapper.findComponent(LoginForm).vm.$emit('login', { password: 'p', username: 'alice' });
    await nextTick();
    expect(clearErrors).toHaveBeenCalled();
    expect(userLogin).toHaveBeenCalledWith({ password: 'p', username: 'alice' });
  });

  it('should drive the controller from the unlock-stage events', async () => {
    const wrapper = mountPage(pinia);
    set(stateRef, { changes: { changes: 1, local: 1, remote: 2, upToVersion: 2 }, kind: UnlockPhase.updatePrompt });
    await nextTick();
    const stage = wrapper.findComponent(LoginUnlockStage);

    stage.vm.$emit('confirm', 2);
    stage.vm.$emit('resolve', { 'eip155:1/erc20:0xabc': 'remote' });
    stage.vm.$emit('skip');
    await nextTick();

    expect(applyUpdate).toHaveBeenCalledWith(undefined, 2);
    expect(applyUpdate).toHaveBeenCalledWith({ 'eip155:1/erc20:0xabc': 'remote' });
    expect(skipUpdate).toHaveBeenCalled();
  });
});
