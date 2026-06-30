import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope } from 'vue';
import { useMainStore } from '@/modules/core/common/use-main-store';
import { useAutoLogin } from './use-auto-login';

const { checkIfPasswordConfirmationNeeded, confirmPassword, lastLoginRef, needsPasswordConfirmationRef, resetSessionBackend, startResume } = vi.hoisted(() => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { ref: vueRef } = require('vue');
  return {
    checkIfPasswordConfirmationNeeded: vi.fn(),
    confirmPassword: vi.fn(),
    lastLoginRef: vueRef(''),
    needsPasswordConfirmationRef: vueRef(false),
    resetSessionBackend: vi.fn().mockResolvedValue(undefined),
    startResume: vi.fn().mockResolvedValue(undefined),
  };
});

vi.mock('@/modules/auth/account-management', () => ({ lastLogin: lastLoginRef }));

vi.mock('@/modules/auth/unlock-flow/use-unlock-flow-controller', () => ({
  useUnlockFlowController: vi.fn(() => ({ startResume })),
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

describe('useAutoLogin', () => {
  let scope: EffectScope;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    set(lastLoginRef, '');
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  it('should resume the session when the backend connects and a profile is saved', async () => {
    set(lastLoginRef, 'alice');
    const autoLogin = scope.run(() => useAutoLogin());

    connect(true);
    await flushPromises();

    expect(resetSessionBackend).toHaveBeenCalled();
    expect(startResume).toHaveBeenCalledTimes(1);
    expect(get(autoLogin!.autolog)).toBe(false);
  });

  it('should not resume when there is no saved profile', async () => {
    scope.run(() => useAutoLogin());

    connect(true);
    await flushPromises();

    expect(resetSessionBackend).toHaveBeenCalled();
    expect(startResume).not.toHaveBeenCalled();
  });

  it('should ignore the disconnect transition', async () => {
    set(lastLoginRef, 'alice');
    scope.run(() => useAutoLogin());

    connect(true);
    await flushPromises();
    startResume.mockClear();

    connect(false);
    await flushPromises();

    expect(startResume).not.toHaveBeenCalled();
  });
});
