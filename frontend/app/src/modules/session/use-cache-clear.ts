import type { DeepReadonly, MaybeRef, Ref } from 'vue';
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface UseCacheClearReturn<T> {
  status: DeepReadonly<Ref<BaseMessage | null>>;
  pending: Readonly<Ref<boolean>>;
  showConfirmation: (source: T) => void;
}

interface Clearable<T> { id: T; text: string }

export function useCacheClear<T>(
  clearable: MaybeRef<Clearable<T>[]>,
  clearHandle: (source: T) => Promise<void>,
  message: (source: string) => {
    success: string;
    error: string;
  },
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

  const clear = async (source: T): Promise<void> => {
    set(confirm, false);
    try {
      set(pending, true);
      await clearHandle(source);
      set(status, {
        error: '',
        success: message(text(source)).success,
      });
      setTimeout(set, 5000, status, null);
    }
    catch {
      set(status, {
        error: message(text(source)).error,
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
