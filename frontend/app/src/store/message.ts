import { SemiPartial } from '@rotki/common';
import { Message } from '@rotki/common/lib/messages';

const emptyMessage = (): Message => ({
  title: '',
  description: '',
  success: false
});

export const useMessageStore = defineStore('message', () => {
  const message = ref(emptyMessage());
  const showMessage = computed(() => get(message).title.length > 0);

  const { tc } = useI18n();

  const setMessage = (
    msg: SemiPartial<Message, 'description'> = emptyMessage()
  ) => {
    set(message, {
      ...{
        title: msg.success
          ? tc('message.success.title')
          : tc('message.error.title'),
        success: false
      },
      ...msg
    });
  };

  const reset = () => {
    set(message, emptyMessage());
  };

  return {
    message,
    showMessage,
    setMessage,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useMessageStore, import.meta.hot));
}
