import type { Ref } from 'vue';
import { promiseTimeout } from '@vueuse/core';

interface UseClearableMessagesReturn {
  clearAll: () => void;
  error: Ref<string>;
  setError: (message: string, useBase?: boolean) => void;
  setSuccess: (message: string, useBase?: boolean) => void;
  stop: () => void;
  success: Ref<string>;
  wait: () => Promise<void>;
}

export function useClearableMessages(): UseClearableMessagesReturn {
  const error = shallowRef<string>('');
  const success = shallowRef<string>('');
  const { t } = useI18n({ useScope: 'global' });

  const clear = (): void => {
    set(success, '');
  };

  const clearAll = (): void => {
    set(error, '');
    set(success, '');
  };

  const formatMessage = (base: string, extra?: string): string => {
    if (extra) {
      if (base)
        return `${base}: ${extra}`;

      return extra;
    }
    return base;
  };

  const setSuccess = (message: string, useBase = false): void => {
    set(success, formatMessage(useBase ? t('settings.saved') : '', message));
  };

  const setError = (message: string, useBase = false): void => {
    set(error, formatMessage(useBase ? t('settings.not_saved') : '', message));
  };

  const wait = async (): Promise<void> => promiseTimeout(200);
  const { start, stop } = useTimeoutFn(clear, 3500);
  watch(success, (success) => {
    if (success)
      start();
  });

  return {
    clearAll,
    error,
    setError,
    setSuccess,
    stop,
    success,
    wait,
  };
}
