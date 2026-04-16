import { describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, ref } from 'vue';
import { type BusyGuard, createPersistentSharedComposable } from './use-persistent-shared-composable';

function withScope(fn: (scope: EffectScope) => void): void {
  const scope = effectScope();
  scope.run(() => fn(scope));
}

describe('createPersistentSharedComposable', () => {
  it('returns the same instance for multiple consumers', () => {
    const useShared = createPersistentSharedComposable(() => {
      const count = ref<number>(0);
      return { count };
    });

    withScope(() => {
      const a = useShared();
      const b = useShared();
      expect(a).toBe(b);
    });
  });

  it('disposes when all consumers unmount and not busy', () => {
    const dispose = vi.fn();
    const useShared = createPersistentSharedComposable(() => {
      const value = ref<number>(1);
      return { dispose, value };
    });

    const scope1 = effectScope();
    scope1.run(() => useShared());

    const scope2 = effectScope();
    scope2.run(() => useShared());

    scope1.stop();
    // Still one subscriber — should not create new instance yet
    const scope3 = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    scope3.run(() => {
      instance = useShared();
    });
    expect(instance!.value.value).toBe(1);

    scope2.stop();
    scope3.stop();

    // All subscribers gone and not busy — state should be disposed
    // Verify by calling again — should get a fresh instance
    const scope4 = effectScope();
    let newInstance: ReturnType<typeof useShared> | undefined;
    scope4.run(() => {
      newInstance = useShared();
    });
    expect(newInstance!.value.value).toBe(1);
    expect(newInstance).not.toBe(instance);
    scope4.stop();
  });

  it('keeps scope alive while busy even with no subscribers', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      const value = ref<number>(42);
      return { value };
    });

    const scope1 = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    scope1.run(() => {
      instance = useShared();
    });

    guard!.acquireBusy();
    scope1.stop();

    // No subscribers but busy — scope should survive
    // Re-subscribe and verify same instance
    const scope2 = effectScope();
    let sameInstance: ReturnType<typeof useShared> | undefined;
    scope2.run(() => {
      sameInstance = useShared();
    });
    expect(sameInstance).toBe(instance);

    guard!.releaseBusy();
    scope2.stop();

    // Now both conditions met — should be disposed
    const scope3 = effectScope();
    let freshInstance: ReturnType<typeof useShared> | undefined;
    scope3.run(() => {
      freshInstance = useShared();
    });
    expect(freshInstance).not.toBe(instance);
    scope3.stop();
  });

  it('preserves state mutated while subscribers are at zero and busy', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      const value = ref<number>(0);
      return { value };
    });

    const scope1 = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    scope1.run(() => {
      instance = useShared();
    });

    // Start work, then unmount all consumers
    guard!.acquireBusy();
    scope1.stop();

    // Mutate state while no subscribers exist (simulates async work updating refs)
    instance!.value.value = 99;

    // Re-subscribe — should get the same instance with the updated value
    const scope2 = effectScope();
    let resubscribed: ReturnType<typeof useShared> | undefined;
    scope2.run(() => {
      resubscribed = useShared();
    });

    expect(resubscribed).toBe(instance);
    expect(resubscribed!.value.value).toBe(99);

    guard!.releaseBusy();
    scope2.stop();
  });

  it('supports multiple acquireBusy calls requiring matching releases', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      const value = ref<string>('test');
      return { value };
    });

    const scope1 = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    scope1.run(() => {
      instance = useShared();
    });

    guard!.acquireBusy();
    guard!.acquireBusy();
    scope1.stop();

    // Release once — still busy
    guard!.releaseBusy();

    const scope2 = effectScope();
    let sameInstance: ReturnType<typeof useShared> | undefined;
    scope2.run(() => {
      sameInstance = useShared();
    });
    expect(sameInstance).toBe(instance);
    scope2.stop();

    // Release second time — now idle, no subscribers → disposed
    guard!.releaseBusy();

    const scope3 = effectScope();
    let freshInstance: ReturnType<typeof useShared> | undefined;
    scope3.run(() => {
      freshInstance = useShared();
    });
    expect(freshInstance).not.toBe(instance);
    scope3.stop();
  });

  it('does not go below zero on extra releaseBusy calls', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      return { ok: true };
    });

    const scope1 = effectScope();
    scope1.run(() => useShared());

    guard!.releaseBusy();
    guard!.releaseBusy();

    // Should still dispose cleanly
    scope1.stop();

    // Fresh instance after disposal
    const scope2 = effectScope();
    let fresh: ReturnType<typeof useShared> | undefined;
    scope2.run(() => {
      fresh = useShared();
    });
    expect(fresh).toBeDefined();
    scope2.stop();
  });
});
