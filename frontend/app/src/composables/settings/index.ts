import { promiseTimeout } from '@vueuse/core';
import type { FrontendSettingsPayload } from '@/types/settings/frontend-settings';
import type { BaseMessage } from '@/types/messages';
import type { SettingsUpdate } from '@/types/user';
import type { SessionSettings } from '@/types/session';
import type { ActionStatus } from '@/types/action';

export enum SettingLocation {
  FRONTEND,
  SESSION,
  GENERAL,
}

interface SuccessfulUpdate {
  success: string;
}

interface UnsuccessfulUpdate {
  error: string;
}

type UpdateResult = SuccessfulUpdate | UnsuccessfulUpdate;

async function getActionStatus(method: () => Promise<ActionStatus>, messages?: BaseMessage): Promise<UpdateResult> {
  let message: UpdateResult = {
    error: messages?.error || '',
  };
  try {
    const result = await method();

    if (result.success) {
      message = {
        success: messages?.success || '',
      };
    }
    else if (result.message) {
      message.error = `${message.error} (${result.message})`;
    }
  }
  catch (error) {
    logger.error(error);
  }

  return message;
}

interface UseSettingsReturn {
  updateSetting: <T extends keyof SettingsUpdate | keyof FrontendSettingsPayload | keyof SessionSettings>(
    settingKey: T,
    settingValue: any,
    settingLocation: SettingLocation,
    message: BaseMessage
  ) => Promise<UpdateResult>;
}

export function useSettings(): UseSettingsReturn {
  const { update: updateSettings } = useSettingsStore();
  const { updateSetting: updateFrontendSettings } = useFrontendSettingsStore();
  const { update: updateSessionSettings } = useSessionSettingsStore();

  const updateSetting = async <T extends keyof SettingsUpdate | keyof FrontendSettingsPayload | keyof SessionSettings>(
    settingKey: T,
    settingValue: any,
    settingLocation: SettingLocation,
    message: BaseMessage,
  ): Promise<UpdateResult> => {
    const payload = { [settingKey]: settingValue };

    const updateMethods: Record<SettingLocation, () => Promise<ActionStatus>> = {
      [SettingLocation.GENERAL]: () => updateSettings(payload),
      [SettingLocation.FRONTEND]: () => updateFrontendSettings(payload),
      [SettingLocation.SESSION]: () => Promise.resolve(updateSessionSettings(payload)),
    };

    return await getActionStatus(updateMethods[settingLocation], message);
  };

  return {
    updateSetting,
  };
}

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
  const error = ref('');
  const success = ref('');
  const { t } = useI18n();

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

  const wait = async (): Promise<void> => await promiseTimeout(200);
  const { start, stop } = useTimeoutFn(clear, 3500);
  watch(success, (success) => {
    if (success)
      start();
  });

  return {
    error,
    success,
    setSuccess,
    setError,
    wait,
    stop,
    clearAll,
  };
}
