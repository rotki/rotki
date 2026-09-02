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

    const firstSubscriber = effectScope();
    firstSubscriber.run(() => useShared());

    const secondSubscriber = effectScope();
    secondSubscriber.run(() => useShared());

    firstSubscriber.stop();

    const subscriberWhileSecondRemains = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    subscriberWhileSecondRemains.run(() => {
      instance = useShared();
    });
    expect(instance!.value.value).toBe(1);

    secondSubscriber.stop();
    subscriberWhileSecondRemains.stop();

    const subscriberAfterAllLeft = effectScope();
    let newInstance: ReturnType<typeof useShared> | undefined;
    subscriberAfterAllLeft.run(() => {
      newInstance = useShared();
    });
    expect(newInstance!.value.value).toBe(1);
    expect(newInstance).not.toBe(instance);
    subscriberAfterAllLeft.stop();
  });

  it('keeps scope alive while busy even with no subscribers', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      const value = ref<number>(42);
      return { value };
    });

    const firstSubscriber = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    firstSubscriber.run(() => {
      instance = useShared();
    });

    guard!.acquireBusy();
    firstSubscriber.stop();

    const subscriberWhileBusy = effectScope();
    let sameInstance: ReturnType<typeof useShared> | undefined;
    subscriberWhileBusy.run(() => {
      sameInstance = useShared();
    });
    expect(sameInstance).toBe(instance);

    guard!.releaseBusy();
    subscriberWhileBusy.stop();

    const subscriberAfterBusyReleased = effectScope();
    let freshInstance: ReturnType<typeof useShared> | undefined;
    subscriberAfterBusyReleased.run(() => {
      freshInstance = useShared();
    });
    expect(freshInstance).not.toBe(instance);
    subscriberAfterBusyReleased.stop();
  });

  it('preserves state mutated while subscribers are at zero and busy', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      const value = ref<number>(0);
      return { value };
    });

    const firstSubscriber = effectScope();
    let instance: ReturnType<typeof useShared> | undefined;
    firstSubscriber.run(() => {
      instance = useShared();
    });

    guard!.acquireBusy();
    firstSubscriber.stop();

    const writtenWhileNobodySubscribed = 99;
    instance!.value.value = writtenWhileNobodySubscribed;

    const resubscriber = effectScope();
    let resubscribed: ReturnType<typeof useShared> | undefined;
    resubscriber.run(() => {
      resubscribed = useShared();
    });

    expect(resubscribed).toBe(instance);
    expect(resubscribed!.value.value).toBe(writtenWhileNobodySubscribed);

    guard!.releaseBusy();
    resubscriber.stop();
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

  it('should still dispose cleanly, and rebuild afterwards, when releaseBusy is called too often', () => {
    let guard: BusyGuard | undefined;
    const useShared = createPersistentSharedComposable((g: BusyGuard) => {
      guard = g;
      return { ok: true };
    });

    const scope1 = effectScope();
    scope1.run(() => useShared());

    guard!.releaseBusy();
    guard!.releaseBusy();

    scope1.stop();

    const scope2 = effectScope();
    let fresh: ReturnType<typeof useShared> | undefined;
    scope2.run(() => {
      fresh = useShared();
    });
    expect(fresh).toBeDefined();
    scope2.stop();
  });
});
