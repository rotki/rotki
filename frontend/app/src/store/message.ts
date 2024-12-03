import type { Message, SemiPartial } from '@rotki/common';

export const useMessageStore = defineStore('message', () => {
  const message = ref<Message>();
  const showMessage = computed(() => isDefined(message));

  const { t } = useI18n();

  const setMessage = (msg?: SemiPartial<Message, 'description'>): void => {
    if (!msg) {
      set(message, undefined);
      return;
    }
    set(message, {
      ...{
        title: msg.success ? t('message.success.title') : t('message.error.title'),
        success: false,
      },
      ...msg,
    });
  };

  return {
    message,
    showMessage,
    setMessage,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMessageStore, import.meta.hot));
