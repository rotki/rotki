import type { DeepReadonly, MaybeRef, Ref } from 'vue';
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface UseCacheClearReturn<T> {
  status: DeepReadonly<Ref<BaseMessage | null>>;
  pending: Readonly<Ref<boolean>>;
  showConfirmation: (source: T) => void;
}

interface Clearable<T> { id: T; text: string }

interface ClearMessages {
  success: (source: string) => string;
  /** `message` is the rejection's own text, which the screen shows after the failure. */
  error: (source: string, message: string) => string;
}

export function useCacheClear<T>(
  clearable: MaybeRef<Clearable<T>[]>,
  clearHandle: (source: T) => Promise<void>,
  message: ClearMessages,
  confirmText: (
    textSource: string,
    source: T,
  ) => {
    title: string;
    message: string;
  },
): UseCacheClearReturn<T> {
  const status = shallowRef<BaseMessage | null>(null);
  const confirm = shallowRef<boolean>(false);
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

  const clear = async (source: T): Promise<void> => {
    set(confirm, false);
    try {
      set(pending, true);
      await clearHandle(source);
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
  };

  const { show } = useConfirmStore();
  const showConfirmation = (source: T): void => {
    show(confirmText(text(source), source), async () => clear(source));
    set(confirm, true);
  };

  return {
    pending: readonly(pending),
    showConfirmation,
    status: readonly(status),
  };
}
