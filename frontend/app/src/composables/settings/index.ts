import { promiseTimeout } from '@vueuse/core';
import { type FrontendSettingsPayload } from '@/types/settings/frontend-settings';
import { type BaseMessage } from '@/types/messages';
import { type SettingsUpdate } from '@/types/user';
import { type SessionSettings } from '@/types/session';
import { type ActionStatus } from '@/types/action';

export enum SettingLocation {
  FRONTEND,
  SESSION,
  GENERAL
}

interface SuccessfulUpdate {
  success: string;
}

interface UnsuccessfulUpdate {
  error: string;
}

type UpdateResult = SuccessfulUpdate | UnsuccessfulUpdate;

const getActionStatus = async (
  method: () => Promise<ActionStatus>,
  messages?: BaseMessage
) => {
  let message: UpdateResult = {
    error: messages?.error || ''
  };
  try {
    const result = await method();

    if (result.success) {
      message = {
        success: messages?.success || ''
      };
    } else if (result.message) {
      message.error = `${message.error} (${result.message})`;
    }
  } catch (e) {
    logger.error(e);
  }

  return message;
};

export const useSettings = () => {
  const { update: updateSettings } = useSettingsStore();
  const { updateSetting: updateFrontendSettings } = useFrontendSettingsStore();
  const { update: updateSessionSettings } = useSessionSettingsStore();

  const updateSetting = async <
    T extends
      | keyof SettingsUpdate
      | keyof FrontendSettingsPayload
      | keyof SessionSettings
  >(
    settingKey: T,
    settingValue: any,
    settingLocation: SettingLocation,
    message: BaseMessage
  ) => {
    const payload = { [settingKey]: settingValue };

    const updateMethods: Record<SettingLocation, () => Promise<ActionStatus>> =
      {
        [SettingLocation.GENERAL]: () => updateSettings(payload),
        [SettingLocation.FRONTEND]: () => updateFrontendSettings(payload),
        [SettingLocation.SESSION]: async () => updateSessionSettings(payload)
      };

    return await getActionStatus(updateMethods[settingLocation], message);
  };

  return {
    updateSetting
  };
};

export const useClearableMessages = () => {
  const error = ref('');
  const success = ref('');
  const { t } = useI18n();

  const clear = () => {
    set(error, '');
    set(success, '');
  };

  const formatMessage = (base: string, extra?: string) => {
    if (extra) {
      if (base) {
        return `${base}: ${extra}`;
      }
      return extra;
    }
    return base;
  };

  const setSuccess = (message: string, useBase = true) => {
    set(success, formatMessage(useBase ? t('settings.saved') : '', message));
  };

  const setError = (message: string, useBase = true) => {
    set(error, formatMessage(useBase ? t('settings.not_saved') : '', message));
  };

  const wait = async () => await promiseTimeout(200);
  const { start, stop } = useTimeoutFn(clear, 3500);
  watch([error, success], ([error, success]) => {
    if (error || success) {
      start();
    }
  });

  return {
    error,
    success,
    setSuccess,
    setError,
    wait,
    stop,
    clear
  };
};
