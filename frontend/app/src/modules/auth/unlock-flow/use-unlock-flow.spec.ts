import { err, none, ok, some } from 'plainfp';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { watch } from 'vue';
import {
  UnlockErrorKind,
  UnlockPhase,
  type UnlockSteps,
  UpdateOutcomeKind,
  useUnlockFlow,
} from './use-unlock-flow';

const CREDENTIALS = { password: 'pw', username: 'alice' };

function makeSteps(overrides: Partial<UnlockSteps> = {}): UnlockSteps {
  return {
    applyUpdate: vi.fn(async () => ok({ kind: UpdateOutcomeKind.done })),
    authenticate: vi.fn(async () => ok(undefined)),
    checkUpdate: vi.fn(async () => ok(none)),
    connect: vi.fn(async () => ok(undefined)),
    loadSession: vi.fn(async () => ok({})),
    login: vi.fn(async () => ok(undefined)),
    probeSession: vi.fn(async () => ok(false)),
    requestRestart: vi.fn(async () => ok(undefined)),
    resolveCredentials: vi.fn(async () => ok(some(CREDENTIALS))),
    resume: vi.fn(async () => ok(undefined)),
    waitReady: vi.fn(async () => ok(undefined)),
    ...overrides,
  };
}

describe('useUnlockFlow', () => {
  let phases: string[];

  function track(flow: ReturnType<typeof useUnlockFlow>): void {
    watch(flow.state, state => phases.push(state.kind), { flush: 'sync', immediate: true });
  }

  beforeEach(() => {
    phases = [];
  });

  it('should walk authenticate → probe → check → login → ready when no session/update exists', async () => {
    const steps = makeSteps();
    const flow = useUnlockFlow(steps);
    track(flow);

    await flow.start(CREDENTIALS);

    expect(phases).toEqual([
      UnlockPhase.idle,
      UnlockPhase.authenticating,
      UnlockPhase.connecting,
      UnlockPhase.probing,
      UnlockPhase.checkingUpdate,
      UnlockPhase.unlocking,
      UnlockPhase.loadingSession,
      UnlockPhase.ready,
    ]);
    expect(steps.login).toHaveBeenCalledTimes(1);
    expect(steps.resume).not.toHaveBeenCalled();
    expect(steps.requestRestart).not.toHaveBeenCalled();
  });

  it('should skip checkUpdate and resume when the backend has a live session', async () => {
    const steps = makeSteps({
      checkUpdate: vi.fn(async () => ok(some({ changes: 5, local: 37, remote: 42, upToVersion: 42 }))),
      probeSession: vi.fn(async () => ok(true)),
    });
    const flow = useUnlockFlow(steps);
    track(flow);

    await flow.start(CREDENTIALS);

    expect(phases).toEqual([
      UnlockPhase.idle,
      UnlockPhase.authenticating,
      UnlockPhase.connecting,
      UnlockPhase.probing,
      UnlockPhase.unlocking,
      UnlockPhase.loadingSession,
      UnlockPhase.ready,
    ]);
    expect(steps.checkUpdate).not.toHaveBeenCalled();
    expect(steps.resume).toHaveBeenCalledTimes(1);
    expect(steps.login).not.toHaveBeenCalled();
    expect(flow.state.value).toMatchObject({ kind: UnlockPhase.ready, resumed: true });
  });

  it('should suspend at update-prompt, then apply → restart → re-auth → ready', async () => {
    const steps = makeSteps({
      checkUpdate: vi.fn(async () => ok(some({ changes: 5, local: 37, remote: 42, upToVersion: 42 }))),
    });
    const flow = useUnlockFlow(steps);
    track(flow);

    await flow.start(CREDENTIALS);
    // suspended waiting for the user's decision
    expect(flow.state.value.kind).toBe(UnlockPhase.updatePrompt);
    expect(steps.login).not.toHaveBeenCalled();

    await flow.applyUpdate();

    expect(phases).toEqual([
      UnlockPhase.idle,
      UnlockPhase.authenticating,
      UnlockPhase.connecting,
      UnlockPhase.probing,
      UnlockPhase.checkingUpdate,
      UnlockPhase.updatePrompt,
      UnlockPhase.applyingUpdate,
      UnlockPhase.restarting,
      UnlockPhase.unlocking,
      UnlockPhase.loadingSession,
      UnlockPhase.ready,
    ]);
    expect(steps.applyUpdate).toHaveBeenCalledWith(42, undefined);
    // re-authenticated and reconnected after the restart (initial + post-restart)
    expect(steps.authenticate).toHaveBeenCalledTimes(2);
    expect(steps.connect).toHaveBeenCalledTimes(2);
    // the session was not resumable, so a fresh login runs after the restart
    expect(flow.state.value).toMatchObject({ kind: UnlockPhase.ready, resumed: false });
  });

  it('should surface conflicts and resume on resolution', async () => {
    const applyUpdate = vi.fn()
      .mockResolvedValueOnce(ok({ conflicts: [], kind: UpdateOutcomeKind.conflicts }))
      .mockResolvedValueOnce(ok({ kind: UpdateOutcomeKind.done }));
    const steps = makeSteps({
      applyUpdate,
      checkUpdate: vi.fn(async () => ok(some({ changes: 2, local: 5, remote: 7, upToVersion: 7 }))),
    });
    const flow = useUnlockFlow(steps);
    track(flow);

    await flow.start(CREDENTIALS);
    await flow.applyUpdate();
    expect(flow.state.value.kind).toBe(UnlockPhase.conflicts);

    await flow.applyUpdate({ 'eip155:1/erc20:0xabc': 'remote' });
    expect(flow.state.value.kind).toBe(UnlockPhase.ready);
    expect(applyUpdate).toHaveBeenLastCalledWith(7, { 'eip155:1/erc20:0xabc': 'remote' });
  });

  it('should skip straight to login when the user declines the update', async () => {
    const steps = makeSteps({
      checkUpdate: vi.fn(async () => ok(some({ changes: 1, local: 2, remote: 3, upToVersion: 3 }))),
    });
    const flow = useUnlockFlow(steps);
    track(flow);

    await flow.start(CREDENTIALS);
    await flow.skipUpdate();

    expect(flow.state.value.kind).toBe(UnlockPhase.ready);
    expect(steps.applyUpdate).not.toHaveBeenCalled();
    expect(steps.requestRestart).not.toHaveBeenCalled();
    expect(steps.login).toHaveBeenCalledTimes(1);
  });

  it('should land in error on a wrong password without probing or unlocking', async () => {
    const steps = makeSteps({
      authenticate: vi.fn(async () => err({ kind: UnlockErrorKind.wrongPassword })),
    });
    const flow = useUnlockFlow(steps);
    track(flow);

    await flow.start(CREDENTIALS);

    expect(flow.state.value).toMatchObject({
      error: { kind: UnlockErrorKind.wrongPassword },
      kind: UnlockPhase.error,
    });
    expect(steps.probeSession).not.toHaveBeenCalled();
    expect(steps.checkUpdate).not.toHaveBeenCalled();
    expect(steps.login).not.toHaveBeenCalled();
  });

  describe('startAuto', () => {
    it('should resolve stored credentials then resume a live session', async () => {
      const steps = makeSteps({ probeSession: vi.fn(async () => ok(true)) });
      const flow = useUnlockFlow(steps);
      track(flow);

      await flow.startAuto();

      expect(phases).toEqual([
        UnlockPhase.idle,
        UnlockPhase.resolving,
        UnlockPhase.authenticating,
        UnlockPhase.connecting,
        UnlockPhase.probing,
        UnlockPhase.unlocking,
        UnlockPhase.loadingSession,
        UnlockPhase.ready,
      ]);
      expect(steps.resume).toHaveBeenCalledTimes(1);
      expect(steps.login).not.toHaveBeenCalled();
    });

    it('should resolve stored credentials then fresh-login when no live session exists', async () => {
      const steps = makeSteps(); // probeSession → false, resolveCredentials → some(CREDENTIALS)
      const flow = useUnlockFlow(steps);
      track(flow);

      await flow.startAuto();

      expect(flow.state.value).toMatchObject({ kind: UnlockPhase.ready, resumed: false });
      expect(steps.login).toHaveBeenCalledTimes(1);
      expect(steps.resume).not.toHaveBeenCalled();
    });

    it('should return to idle when nothing is stored', async () => {
      const steps = makeSteps({ resolveCredentials: vi.fn(async () => ok(none)) });
      const flow = useUnlockFlow(steps);
      track(flow);

      await flow.startAuto();

      expect(flow.state.value.kind).toBe(UnlockPhase.idle);
      expect(steps.probeSession).not.toHaveBeenCalled();
    });

    it('should return to idle when there is no live session and no saved password', async () => {
      const steps = makeSteps({
        probeSession: vi.fn(async () => ok(false)),
        resolveCredentials: vi.fn(async () => ok(some({ password: '', username: 'alice' }))),
      });
      const flow = useUnlockFlow(steps);
      track(flow);

      await flow.startAuto();

      // no doomed empty-password login — straight back to the idle form
      expect(flow.state.value.kind).toBe(UnlockPhase.idle);
      expect(steps.login).not.toHaveBeenCalled();
    });
  });
});
