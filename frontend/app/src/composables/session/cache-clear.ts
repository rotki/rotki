import { type Ref } from 'vue';
import { type BaseMessage } from '@/types/messages';

export const useCacheClear = <T>(
  clearable: { id: T; text: string }[],
  clearHandle: (source: T) => Promise<void>,
  message: (source: string) => {
    success: string;
    error: string;
  },
  confirmText: (source: string) => {
    title: string;
    message: string;
  }
) => {
  const status: Ref<BaseMessage | null> = ref(null);
  const confirm: Ref<boolean> = ref(false);
  const pending: Ref<boolean> = ref(false);

  const text = (source: T): string =>
    clearable.find(({ id }) => id === source)?.text || '';

  const clear = async (source: T) => {
    set(confirm, false);
    try {
      set(pending, true);
      await clearHandle(source);
      set(status, {
        success: message(text(source)).success,
        error: ''
      });
      setTimeout(() => set(status, null), 5000);
    } catch {
      set(status, {
        error: message(text(source)).error,
        success: ''
      });
    } finally {
      set(pending, false);
    }
  };

  const { show } = useConfirmStore();
  const showConfirmation = (source: T) => {
    show(confirmText(text(source)), async () => clear(source));
    set(confirm, true);
  };

  return {
    status,
    pending,
    showConfirmation
  };
};
