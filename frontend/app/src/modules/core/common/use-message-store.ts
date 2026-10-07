import type { Message, SemiPartial } from '@rotki/common';
import { logger } from '@/modules/core/common/logging/logging';
import { hasLiveSession } from '@/modules/core/session/session-lifecycle';

interface SetMessageOptions {
  /** Shows the dialog even with no live session. */
  readonly sessionless?: boolean;
}

export const useMessageStore = defineStore('message', () => {
  const message = ref<Message>();
  const showMessage = computed(() => isDefined(message));

  const { t } = useI18n({ useScope: 'global' });

  /**
   * Shows the message dialog, or clears it when called without a message.
   *
   * @remarks
   * A message raised while no session is live is dropped, unless `options.sessionless` says it
   * belongs to the logged-out screen (a logout that failed after its session ended). Anything else
   * arriving then comes from session work that outlived its logout: a request the session gate
   * refused, a handler that resumed late. Clearing always goes through.
   */
  const setMessage = (msg?: SemiPartial<Message, 'description'>, options?: SetMessageOptions): void => {
    if (!msg) {
      set(message, undefined);
      return;
    }
    if (!options?.sessionless && !hasLiveSession()) {
      logger.debug(`dropped message with no live session: ${msg.title ?? msg.description}`);
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
