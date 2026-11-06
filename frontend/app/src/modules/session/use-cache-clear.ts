import type { DeepReadonly, MaybeRef, Ref } from 'vue';
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';

interface UseCacheClearReturn<T> {
  status: DeepReadonly<Ref<BaseMessage | null>>;
  pending: Readonly<Ref<boolean>>;
  /**
   * Clears `source` straight away and settles once the clear has.
   *
   * @remarks
   * A clear that loses something the user cannot fetch again (purged data) is confirmed by its
   * trigger before this is called.
   */
  request: (source: T) => Promise<void>;
}

interface Clearable<T> { id: T; text: string }

interface ClearMessages {
  success: (source: string) => string;
  /** `message` is the rejection's own text, which the screen shows after the failure. */
  error: (source: string, message: string) => string;
}

/**
 * Runs a cache clear and keeps its outcome for the screen.
 *
 * @param clearable - the sources, with the text the messages name them by
 * @param clearHandle - the clear; resolves `false` when it did not happen and needs no message,
 * such as a cancelled run
 * @param message - what the screen says after the clear
 */
export function useCacheClear<T>(
  clearable: MaybeRef<Clearable<T>[]>,
  clearHandle: (source: T) => Promise<boolean | void>,
  message: ClearMessages,
): UseCacheClearReturn<T> {
  const status = shallowRef<BaseMessage | null>(null);
  const pending = shallowRef<boolean>(false);

  const text = (source: T): string => get(clearable).find(({ id }) => id === source)?.text ?? '';

  /**
   * Drops the success message a few seconds after a purge.
   *
   * @remarks
   * `useTimeoutFn` ties the timer to this composable's scope, so a pending reset cannot write to
   * `status` once the owner is gone, and a second purge restarts the window rather than stacking
   * a second timer on top of the first.
   */
  const { start: scheduleStatusReset } = useTimeoutFn(() => {
    set(status, null);
  }, 5000, { immediate: false });

  async function clear(source: T): Promise<void> {
    try {
      set(pending, true);
      if (await clearHandle(source) === false)
        return;
      set(status, {
        error: '',
        success: message.success(text(source)),
      });
      scheduleStatusReset();
    }
    catch (error: unknown) {
      set(status, {
        error: message.error(text(source), getErrorMessage(error)),
        success: '',
      });
    }
    finally {
      set(pending, false);
    }
  }

  return {
    pending: readonly(pending),
    request: clear,
    status: readonly(status),
  };
}
