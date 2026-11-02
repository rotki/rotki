import type { MaybeRefOrGetter, Ref } from 'vue';
import type { BankAuthChallenge } from '@/modules/banks/types';
import { startPromise } from '@shared/utils';

const DEFAULT_POLL_DELAY_SECONDS = 5;

/**
 * Polls a bank while an approval is pending in its app.
 *
 * @remarks
 * FinTS has no callback from the phone to rotki. Each challenge carries the delay advertised by
 * the bank; when it is absent, polling falls back to five seconds. A failed poll stops the loop so
 * the dialog can expose its error and let the user retry manually.
 */
export function useBankAuthenticationPolling(
  challenge: MaybeRefOrGetter<BankAuthChallenge | undefined>,
  poll: () => Promise<void>,
): Readonly<Ref<boolean>> {
  const polling = shallowRef<boolean>(false);
  let timeout: ReturnType<typeof setTimeout> | undefined;

  onScopeDispose(() => clearTimeout(timeout));

  watch(() => toValue(challenge), (current) => {
    set(polling, false);
    if (current?.primitive !== 'app approval poll')
      return;

    set(polling, true);
    timeout = setTimeout(() => {
      startPromise((async (): Promise<void> => {
        try {
          await poll();
        }
        finally {
          if (toValue(challenge) === current)
            set(polling, false);
        }
      })());
    }, Math.max(current.pollDelaySeconds ?? DEFAULT_POLL_DELAY_SECONDS, 1) * 1000);
    onWatcherCleanup(() => clearTimeout(timeout));
  }, { immediate: true });

  return readonly(polling);
}
