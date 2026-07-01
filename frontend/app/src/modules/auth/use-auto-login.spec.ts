import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope } from 'vue';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { createAutoLogin } from './use-auto-login';

const { checkIfPasswordConfirmationNeeded, confirmPassword, controllerStateRef, lastLoginRef, needsPasswordConfirmationRef, resetSessionBackend, startAuto } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    checkIfPasswordConfirmationNeeded: vi.fn(),
    confirmPassword: vi.fn(),
    controllerStateRef: vueRef({ kind: 'idle' }),
    lastLoginRef: vueRef(''),
    needsPasswordConfirmationRef: vueRef(false),
    resetSessionBackend: vi.fn().mockResolvedValue(undefined),
    startAuto: vi.fn().mockResolvedValue(undefined),
  };
});

vi.mock('@/modules/auth/account-management', () => ({ lastLogin: lastLoginRef }));

vi.mock('@/modules/auth/unlock-flow/use-unlock-flow-controller', () => ({
  useUnlockFlowController: vi.fn(() => ({ startAuto, state: controllerStateRef })),
}));

vi.mock('@/modules/auth/use-password-confirmation', () => ({
  usePasswordConfirmation: vi.fn(() => ({
    checkIfPasswordConfirmationNeeded,
    confirmPassword,
    needsPasswordConfirmation: needsPasswordConfirmationRef,
  })),
}));

vi.mock('@/modules/shell/app/use-backend-management', () => ({
  useBackendManagement: vi.fn(() => ({ resetSessionBackend })),
}));

function connect(value: boolean): void {
  set(storeToRefs(useMainStore()).connected, value);
}

describe('createAutoLogin', () => {
  let scope: EffectScope;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(lastLoginRef, '');
    set(controllerStateRef, { kind: 'idle' });
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  it('should resume the session when the backend connects and a profile is saved', async () => {
    set(lastLoginRef, 'alice');
    const autoLogin = scope.run(() => createAutoLogin());

    connect(true);
    await flushPromises();

    expect(resetSessionBackend).toHaveBeenCalled();
    expect(startAuto).toHaveBeenCalledTimes(1);
    expect(get(autoLogin!.autolog)).toBe(false);
  });

  it('should keep the loader up on a successful auto-unlock while navigation is pending', async () => {
    set(lastLoginRef, 'alice');
    // success ⇒ the flow ends in `ready` and navigation runs asynchronously
    startAuto.mockImplementation(async () => set(controllerStateRef, { kind: 'ready' }));
    const autoLogin = scope.run(() => createAutoLogin());

    connect(true);
    await flushPromises();

    expect(get(autoLogin!.autolog)).toBe(true);
  });

  it('should not resume when there is no saved profile', async () => {
    scope.run(() => createAutoLogin());

    connect(true);
    await flushPromises();

    expect(resetSessionBackend).toHaveBeenCalled();
    expect(startAuto).not.toHaveBeenCalled();
  });

  it('should ignore the disconnect transition', async () => {
    set(lastLoginRef, 'alice');
    scope.run(() => createAutoLogin());

    connect(true);
    await flushPromises();
    startAuto.mockClear();

    connect(false);
    await flushPromises();

    expect(startAuto).not.toHaveBeenCalled();
  });
});
