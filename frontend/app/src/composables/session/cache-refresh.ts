import { type Ref } from 'vue';
import { type BaseMessage } from '@/types/messages';
import { type OtherPurge } from '@/types/session/purge';

export const useCacheRefresh = (
  purgable: { id: OtherPurge; text: string }[],
  purgeSource: (source: OtherPurge) => Promise<void>,
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

  const text = (source: OtherPurge): string =>
    purgable.find(({ id }) => id === source)?.text || '';

  const purge = async (source: OtherPurge) => {
    set(confirm, false);
    try {
      set(pending, true);
      await purgeSource(source);
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
  const showConfirmation = (source: OtherPurge) => {
    show(confirmText(text(source)), async () => purge(source));
    set(confirm, true);
  };

  return {
    status,
    pending,
    showConfirmation
  };
};
