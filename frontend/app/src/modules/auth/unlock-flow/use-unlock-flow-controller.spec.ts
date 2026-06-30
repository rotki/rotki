import { flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { none, ok, some } from 'plainfp';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope } from 'vue';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { api } from '@/modules/core/api/rotki-api';
import { logger } from '@/modules/core/common/logging/logging';
import { UnlockErrorKind, UnlockPhase } from './use-unlock-flow';
import { createUnlockFlowController, type UseUnlockFlowControllerReturn } from './use-unlock-flow-controller';

vi.mock('@/modules/core/api/rotki-api', () => ({
  api: { setOnAuthFailure: vi.fn() },
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

const h = vi.hoisted(() => ({
  applyUpdate: vi.fn(),
  authenticate: vi.fn(),
  checkIfPasswordConfirmationNeeded: vi.fn(),
  checkUpdate: vi.fn(),
  connect: vi.fn(),
  createCheckUpdate: vi.fn(),
  createUnlock: vi.fn(),
  disconnectWallet: vi.fn(),
  handleSessionReady: vi.fn(),
  loadSession: vi.fn(),
  requestRestart: vi.fn(),
  unlock: vi.fn(),
  updateFrontendSetting: vi.fn(),
  waitReady: vi.fn(),
}));

vi.mock('./use-unlock-steps', () => ({
  useUnlockSteps: (): unknown => ({
    createSteps: vi.fn(() => ({
      applyUpdate: h.applyUpdate,
      authenticate: h.authenticate,
      checkUpdate: h.createCheckUpdate,
      connect: h.connect,
      loadSession: h.loadSession,
      requestRestart: h.requestRestart,
      unlock: h.createUnlock,
      waitReady: h.waitReady,
    })),
    loginSteps: {
      applyUpdate: h.applyUpdate,
      authenticate: h.authenticate,
      checkUpdate: h.checkUpdate,
      connect: h.connect,
      loadSession: h.loadSession,
      requestRestart: h.requestRestart,
      unlock: h.unlock,
      waitReady: h.waitReady,
    },
  }),
}));

vi.mock('./use-session-ready', () => ({
  useSessionReady: (): unknown => ({ handleSessionReady: h.handleSessionReady }),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): unknown => ({ updateFrontendSetting: h.updateFrontendSetting }),
}));

vi.mock('@/modules/wallet/use-wallet-store', () => ({
  useWalletStore: (): unknown => ({ disconnect: h.disconnectWallet }),
}));

vi.mock('@/modules/auth/use-remember-settings', () => ({
  useRememberSettings: (): unknown => ({ savedUsername: ref<string | null>(null) }),
}));

vi.mock('@/modules/auth/use-password-confirmation', () => ({
  usePasswordConfirmation: (): unknown => ({ checkIfPasswordConfirmationNeeded: h.checkIfPasswordConfirmationNeeded }),
}));

function setUsernameOnLoad(name: string): void {
  const { username } = storeToRefs(useSessionAuthStore());
  h.loadSession.mockImplementation(async () => {
    set(username, name);
    return ok({ username: name });
  });
}

describe('useUnlockFlowController', () => {
  let scope: EffectScope;
  let controller: UseUnlockFlowControllerReturn;

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    h.authenticate.mockResolvedValue(ok(undefined));
    h.connect.mockResolvedValue(ok(undefined));
    h.checkUpdate.mockResolvedValue(ok(none));
    h.createCheckUpdate.mockResolvedValue(ok(none));
    h.applyUpdate.mockResolvedValue(ok({ kind: 'done' }));
    h.requestRestart.mockResolvedValue(ok(undefined));
    h.waitReady.mockResolvedValue(ok(undefined));
    h.unlock.mockResolvedValue(ok(undefined));
    h.createUnlock.mockResolvedValue(ok(undefined));
    setUsernameOnLoad('alice');

    scope = effectScope();
    const created = scope.run(() => createUnlockFlowController());
    if (!created)
      throw new Error('controller not created');
    controller = created;
  });

  afterEach(() => {
    scope.stop();
  });

  it('should drive a fresh login to ready and run login-mode side-effects', async () => {
    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.ready);
    expect(h.handleSessionReady).toHaveBeenCalled();
    expect(h.updateFrontendSetting).toHaveBeenCalled();
    expect(h.disconnectWallet).toHaveBeenCalled();
    expect(h.checkIfPasswordConfirmationNeeded).not.toHaveBeenCalled();
  });

  it('should drive account creation to ready without login-only effects', async () => {
    setUsernameOnLoad('bob');
    await controller.startCreate({ credentials: { password: 'p', username: 'bob' }, initialSettings: { submitUsageAnalytics: true } });
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.ready);
    expect(h.createUnlock).toHaveBeenCalled();
    expect(h.handleSessionReady).toHaveBeenCalled();
    expect(h.updateFrontendSetting).not.toHaveBeenCalled();
    expect(h.disconnectWallet).not.toHaveBeenCalled();
  });

  it('should fall back to idle when a resume finds no live session', async () => {
    h.unlock.mockResolvedValue({ error: { kind: UnlockErrorKind.unknown, message: '' }, ok: false });

    await controller.startResume();
    await flushPromises();

    // a failed background resume must not park the flow in error — it returns to a clean form
    expect(get(controller.state).kind).toBe(UnlockPhase.idle);
  });

  it('should skip the asset-update prompt on resume even when an update exists', async () => {
    h.checkUpdate.mockResolvedValue(ok(some({ upToVersion: 9 })));

    await controller.startResume();
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.ready);
    expect(h.checkIfPasswordConfirmationNeeded).toHaveBeenCalled();
    expect(h.updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should suspend at the update prompt, then complete through apply + restart', async () => {
    h.checkUpdate.mockResolvedValue(ok(some({ upToVersion: 9 })));

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();
    expect(get(controller.state).kind).toBe(UnlockPhase.updatePrompt);

    await controller.applyUpdate();
    await flushPromises();

    expect(h.requestRestart).toHaveBeenCalled();
    expect(get(controller.state).kind).toBe(UnlockPhase.ready);
  });

  it('should ignore a second start while a flow is already in flight', async () => {
    h.checkUpdate.mockResolvedValue(ok(some({ upToVersion: 9 })));

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();
    expect(get(controller.state).kind).toBe(UnlockPhase.updatePrompt);

    // a resume firing mid-flow (e.g. an auto-login watcher) must be ignored
    await controller.startResume();
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.updatePrompt);
    expect(h.checkIfPasswordConfirmationNeeded).not.toHaveBeenCalled();
  });

  it('should expose an unknown unlock error as a message in errors', async () => {
    h.unlock.mockResolvedValue({ error: { kind: UnlockErrorKind.unknown, message: 'boom' }, ok: false });

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.error);
    expect(get(controller.errors)).toEqual(['boom']);
    expect(get(controller.loading)).toBe(false);
    expect(logger.error).toHaveBeenCalledWith(expect.stringContaining('boom'));
  });

  it('should wire a session-gated 401 handler on the api', () => {
    expect(api.setOnAuthFailure).toHaveBeenCalled();
    const [action, isSessionActive] = vi.mocked(api.setOnAuthFailure).mock.calls.at(-1)!;
    const { logged } = storeToRefs(useSessionAuthStore());

    set(logged, true);
    expect(isSessionActive?.()).toBe(true); // a 401 while logged in is a real session loss
    action();
    expect(get(logged)).toBe(false); // ...and clears the session
    expect(isSessionActive?.()).toBe(false); // a 401 while logged out stays local
  });

  it('should keep errors empty for a sync conflict (the alert is store-driven)', async () => {
    h.unlock.mockResolvedValue({ error: { kind: UnlockErrorKind.syncConflict, payload: {} }, ok: false });

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.error);
    expect(get(controller.errors)).toEqual([]);
  });

  it('should surface a failed asset update as a message', async () => {
    h.checkUpdate.mockResolvedValue(ok(some({ upToVersion: 9 })));
    h.applyUpdate.mockResolvedValue({ error: { kind: UnlockErrorKind.updateFailed, message: 'update boom' }, ok: false });

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();
    await controller.applyUpdate();
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.error);
    expect(get(controller.errors)).toEqual(['update boom']);
  });

  it('should surface a failed restart with a localized message', async () => {
    h.checkUpdate.mockResolvedValue(ok(some({ upToVersion: 9 })));
    h.requestRestart.mockResolvedValue({ error: { kind: UnlockErrorKind.restartFailed }, ok: false });

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();
    await controller.applyUpdate();
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.error);
    expect(get(controller.errors)).toHaveLength(1);
  });

  it('should skip straight to unlock when the user declines the update', async () => {
    h.checkUpdate.mockResolvedValue(ok(some({ upToVersion: 9 })));

    await controller.startLogin({ password: 'p', username: 'alice' });
    await flushPromises();
    expect(get(controller.state).kind).toBe(UnlockPhase.updatePrompt);

    await controller.skipUpdate();
    await flushPromises();

    expect(get(controller.state).kind).toBe(UnlockPhase.ready);
    expect(h.applyUpdate).not.toHaveBeenCalled();
    expect(h.unlock).toHaveBeenCalled();
  });
});
