import type { ActionStatus } from '@/modules/core/common/action';
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import type { SessionSettings } from '@/modules/session/types';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import { logger } from '@/modules/core/common/logging/logging';
import { useSessionSettingsStore } from '@/modules/settings/use-session-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

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
    error: messages?.error ?? '',
  };
  try {
    const result = await method();

    if (result.success) {
      message = {
        success: messages?.success ?? '',
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
    message: BaseMessage,
  ) => Promise<UpdateResult>;
}

export function useSettings(): UseSettingsReturn {
  const { update: updateSettings, updateFrontendSetting: updateFrontendSettings } = useSettingsOperations();
  const { update: updateSessionSettings } = useSessionSettingsStore();

  const updateSetting = async <T extends keyof SettingsUpdate | keyof FrontendSettingsPayload | keyof SessionSettings>(
    settingKey: T,
    settingValue: any,
    settingLocation: SettingLocation,
    message: BaseMessage,
  ): Promise<UpdateResult> => {
    const payload = { [settingKey]: settingValue };

    const updateMethods: Record<SettingLocation, () => Promise<ActionStatus>> = {
      [SettingLocation.FRONTEND]: async () => updateFrontendSettings(payload),
      [SettingLocation.GENERAL]: async () => updateSettings(payload),
      [SettingLocation.SESSION]: async () => Promise.resolve(updateSessionSettings(payload)),
    };

    return getActionStatus(updateMethods[settingLocation], message);
  };

  return {
    updateSetting,
  };
}
