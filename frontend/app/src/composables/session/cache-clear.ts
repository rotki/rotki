import type { MaybeRef } from '@vueuse/core';
import type { Ref } from 'vue';
import type { BaseMessage } from '@/types/messages';
import { useConfirmStore } from '@/store/confirm';

interface UseCacheClearReturn<T> {
  status: Ref<BaseMessage | null>;
  pending: Ref<boolean>;
  showConfirmation: (source: T) => void;
}

export interface Clearable<T> { id: T; text: string }

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
  const status = ref<BaseMessage | null>(null);
  const confirm = ref<boolean>(false);
  const pending = ref<boolean>(false);

  const text = (source: T): string => get(clearable).find(({ id }) => id === source)?.text || '';

  const clear = async (source: T): Promise<void> => {
    set(confirm, false);
    try {
      set(pending, true);
      await clearHandle(source);
      set(status, {
        error: '',
        success: message(text(source)).success,
      });
      setTimeout(() => set(status, null), 5000);
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
    pending,
    showConfirmation,
    status,
  };
}
