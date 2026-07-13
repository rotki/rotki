import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope, type EffectScope, nextTick } from 'vue';
import { useSingleTabGuard } from './use-single-tab-guard';

const logged = ref<boolean>(false);
const isActiveTab = ref<boolean>(true);
const supported = ref<boolean>(true);
const claim = vi.fn(() => set(isActiveTab, true));
const release = vi.fn(() => set(isActiveTab, true));
const start = vi.fn();
const stop = vi.fn();

vi.mock('@/modules/auth/use-session-auth-store', () => ({
  useSessionAuthStore: (): object => ({ logged }),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: (): object => ({ start, stop }),
}));

vi.mock('@/modules/session/single-tab/use-single-tab', () => ({
  useSingleTab: (): object => ({
    claim,
    isActiveTab,
    release,
    get supported(): boolean {
      return get(supported);
    },
  }),
}));

describe('useSingleTabGuard', () => {
  let scope: EffectScope;

  beforeEach(() => {
    vi.clearAllMocks();
    set(logged, false);
    set(isActiveTab, true);
    set(supported, true);
    scope = effectScope();
  });

  afterEach(() => {
    scope.stop();
  });

  it('should claim ownership when the user logs in', async () => {
    scope.run(() => useSingleTabGuard());
    set(logged, true);
    await nextTick();
    expect(claim).toHaveBeenCalledOnce();
    expect(release).not.toHaveBeenCalled();
  });

  it('should release ownership when the user logs out', async () => {
    set(logged, true);
    scope.run(() => useSingleTabGuard());
    set(logged, false);
    await nextTick();
    expect(release).toHaveBeenCalledOnce();
  });

  it('should stop the monitor when another tab takes over', async () => {
    set(logged, true);
    scope.run(() => useSingleTabGuard());
    set(isActiveTab, false);
    await nextTick();
    expect(stop).toHaveBeenCalledOnce();
    expect(start).not.toHaveBeenCalled();
  });

  it('should not restart the monitor in place when ownership returns (reclaim reloads)', async () => {
    set(logged, true);
    scope.run(() => useSingleTabGuard());
    set(isActiveTab, false);
    await nextTick();
    set(isActiveTab, true);
    await nextTick();
    expect(start).not.toHaveBeenCalled();
  });

  it('should not touch the monitor on ownership changes while logged out', async () => {
    scope.run(() => useSingleTabGuard());
    set(isActiveTab, false);
    await nextTick();
    set(isActiveTab, true);
    await nextTick();
    expect(stop).not.toHaveBeenCalled();
    expect(start).not.toHaveBeenCalled();
  });

  it('should do nothing when coordination is unsupported', async () => {
    set(supported, false);
    scope.run(() => useSingleTabGuard());
    set(logged, true);
    await nextTick();
    set(isActiveTab, false);
    await nextTick();
    expect(claim).not.toHaveBeenCalled();
    expect(stop).not.toHaveBeenCalled();
  });
});
