import { type SemiPartial } from '@rotki/common';
import { type Message } from '@rotki/common/lib/messages';

const emptyMessage = (): Message => ({
  title: '',
  description: '',
  success: false
});

export const useMessageStore = defineStore('message', () => {
  const message = ref(emptyMessage());
  const showMessage = computed(() => get(message).title.length > 0);

  const { t } = useI18n();

  const setMessage = (
    msg: SemiPartial<Message, 'description'> = emptyMessage()
  ): void => {
    set(message, {
      ...{
        title: msg.success
          ? t('message.success.title')
          : t('message.error.title'),
        success: false
      },
      ...msg
    });
  };

  return {
    message,
    showMessage,
    setMessage
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMessageStore, import.meta.hot));
}
