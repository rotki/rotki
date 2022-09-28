import { promiseTimeout } from '@vueuse/core';
import { useSettingsStore } from '@/store/settings';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import {
  SessionSettings,
  useSessionSettingsStore
} from '@/store/settings/session';
import { ActionStatus } from '@/store/types';
import { FrontendSettingsPayload } from '@/types/frontend-settings';
import { BaseMessage } from '@/types/messages';
import { SettingsUpdate } from '@/types/user';
import { logger } from '@/utils/logging';

export enum SettingLocation {
  FRONTEND,
  SESSION,
  GENERAL
}

type SuccessfulUpdate = { success: string };
type UnsuccessfulUpdate = { error: string };
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
    } else {
      if (result.message) {
        message.error = `${message.error} (${result.message})`;
      }
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
  const { tc } = useI18n();

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

  const setSuccess = (message: string, useBase: boolean = true) => {
    set(success, formatMessage(useBase ? tc('settings.saved') : '', message));
  };

  const setError = (message: string, useBase: boolean = true) => {
    set(error, formatMessage(useBase ? tc('settings.not_saved') : '', message));
  };

  const wait = async () => await promiseTimeout(200);
  const { start, stop } = useTimeoutFn(clear, 5500);
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
