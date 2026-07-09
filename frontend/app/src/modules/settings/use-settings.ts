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

/**
 * The `SettingLocation` a registered channel is expected to be written through. Routing for registered
 * keys now derives from the registry, so this is only used to warn on a caller/registry mismatch.
 */
function expectedLocation(channel: SettingChannel): SettingLocation {
  if (channel === Channel.frontend)
    return SettingLocation.FRONTEND;
  if (channel === Channel.session)
    return SettingLocation.SESSION;
  return SettingLocation.GENERAL; // general + accounting
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
    // Route every registered key through the single write facade; the owning channel (and its per-key
    // effects/mirrors, including animationsEnabled's localStorage) is derived from the registry. Only
    // unregistered keys (dynamic, wire-named, premium flags) fall through to the location path.
    const channel = channelFor(settingKey);
    if (channel !== undefined) {
      // Routing derives from the registry, so the caller's location is advisory; warn on a mismatch so
      // a future miswiring surfaces instead of being silently ignored.
      if (expectedLocation(channel) !== settingLocation)
        logger.warn(`updateSetting('${settingKey}'): supplied location ${SettingLocation[settingLocation]} does not match its registered channel '${channel}'; routing by registry.`);
      // The generic write<K> can't correlate a widened key with its value, so call it through a
      // non-generic view. channelFor resolving a channel proves the key is writable.
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
