import { type EffectScope, effectScope, onScopeDispose } from 'vue';

/**
 * Like VueUse's `createSharedComposable`, but defers scope disposal while
 * a "busy" guard is active. This prevents the scope (and its refs / watchers)
 * from being destroyed when all consuming components unmount, as long as
 * background work (e.g. an async queue) is still in progress.
 *
 * Disposal happens when **both** conditions are met:
 *  - every consumer has unmounted (`subscribers === 0`)
 *  - `releaseBusy()` has been called for every prior `acquireBusy()`
 *
 * The composable factory receives `{ acquireBusy, releaseBusy }` so the
 * inner logic can signal when it starts/finishes long-running work.
 */

export interface BusyGuard {
  acquireBusy: () => void;
  releaseBusy: () => void;
}

export function createPersistentSharedComposable<T>(
  composable: (guard: BusyGuard) => T,
): () => T {
  let state: T | undefined;
  let scope: EffectScope | undefined;
  let subscribers = 0;
  let busyCount = 0;

  function tryDispose(): void {
    if (subscribers <= 0 && busyCount <= 0 && scope) {
      scope.stop();
      state = undefined;
      scope = undefined;
    }
  }

  function acquireBusy(): void {
    busyCount += 1;
  }

  function releaseBusy(): void {
    busyCount = Math.max(0, busyCount - 1);
    tryDispose();
  }

  return (): T => {
    if (!scope) {
      scope = effectScope(true);
      state = scope.run(() => composable({ acquireBusy, releaseBusy }))!;
    }

    subscribers += 1;
    onScopeDispose(() => {
      subscribers -= 1;
      tryDispose();
    });

    return state!;
  };
}
