import type { Message, SemiPartial } from '@rotki/common';

export const useMessageStore = defineStore('message', () => {
  const message = ref<Message>();
  const showMessage = computed(() => isDefined(message));

  const { t } = useI18n({ useScope: 'global' });

  const setMessage = (msg?: SemiPartial<Message, 'description'>): void => {
    if (!msg) {
      set(message, undefined);
      return;
    }
    set(message, {
      success: false,
      title: msg.success ? t('message.success.title') : t('message.error.title'),
      ...msg,
    });
  };

  return {
    message,
    setMessage,
    showMessage,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useMessageStore, import.meta.hot));
