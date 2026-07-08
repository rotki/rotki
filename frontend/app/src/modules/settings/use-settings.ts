import type { ActionStatus } from '@/modules/core/common/action';
import type { BaseMessage } from '@/modules/core/messaging/base-message';
import type { SessionSettings } from '@/modules/session/types';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import { logger } from '@/modules/core/common/logging/logging';
import { Channel, getRegistryEntry, type SettingChannel } from '@/modules/settings/settings-registry';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useSettingsWriter, type WritableSettingKey } from '@/modules/settings/settings-writer';
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

/**
 * Resolves a setting key to its owning channel via the registry routing table, or `undefined` if the
 * key is not registered (dynamic keys, wire-named keys, premium flags, and write-only settings not yet
 * in the table).
 */
function channelFor(key: string): SettingChannel | undefined {
  return getRegistryEntry(key)?.channel;
}

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
  const { updateSession: updateSessionSettings } = useSettingsRepo();
  const { write } = useSettingsWriter();

  const updateSetting = async <T extends keyof SettingsUpdate | keyof FrontendSettingsPayload | keyof SessionSettings>(
    settingKey: T,
    settingValue: any,
    settingLocation: SettingLocation,
    message: BaseMessage,
  ): Promise<UpdateResult> => {
    // Route registered general/accounting/frontend keys through the single write facade. Session keys
    // keep the location path (animationsEnabled has a bespoke setter that must not fire here), as do
    // unregistered keys (dynamic, wire-named, premium flags).
    const channel = channelFor(settingKey);
    if (channel !== undefined && channel !== Channel.session) {
      // The generic write<K> can't correlate a widened key with its value, so call it through a
      // non-generic view. channelFor resolving a non-session channel proves the key is writable.
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- contained cast to a non-generic writer signature at this boundary
      const writeAny = write as (key: WritableSettingKey, value: unknown) => Promise<ActionStatus>;
      // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- settingKey is a WritableSettingKey here
      return getActionStatus(async () => writeAny(settingKey as WritableSettingKey, settingValue), message);
    }

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
