import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { transformCase } from '@rotki/common';
import { CHAIN_KEYED_SETTINGS, RequestTarget } from '@/modules/core/api/constants';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/core/api/utils';
import { type SettingsUpdate, UserSettingsModel } from '@/modules/settings/types/user-settings';
import { BackendConfiguration, ColibriConfiguration } from '@/modules/shell/app/backend';

interface UseSettingsApiReturn {
  setSettings: (settings: SettingsUpdate) => Promise<UserSettingsModel>;
  patchFrontendSettings: (patch: FrontendSettingsPayload, remove?: string[]) => Promise<void>;
  getFrontendSettings: () => Promise<Record<string, unknown>>;
  getSettings: () => Promise<UserSettingsModel>;
  getRawSettings: () => Promise<SettingsUpdate>;
  backendSettings: () => Promise<BackendConfiguration>;
  updateBackendConfiguration: (loglevel: string) => Promise<BackendConfiguration>;
  colibriSettings: () => Promise<ColibriConfiguration>;
  updateColibriConfiguration: (loglevel: string) => Promise<ColibriConfiguration>;
}

export function useSettingsApi(): UseSettingsApiReturn {
  const setSettings = async (settings: SettingsUpdate): Promise<UserSettingsModel> => {
    const response = await api.put<UserSettingsModel>(
      '/settings',
      { settings },
      { skipCamelCaseKeys: CHAIN_KEYED_SETTINGS },
    );
    return UserSettingsModel.parse(response);
  };

  /**
   * Merges a partial update into the stored frontend settings blob, server-side.
   *
   * @remarks
   * The whole point of merging on the server is that a key the running client's schema does not
   * declare cannot be preserved by the client: it has already been parsed away. Sending only the
   * changed keys leaves such a key untouched instead of overwriting it with a reduced view.
   *
   * Both arguments are camelCase. The shared request transformer renames object *keys*, so `patch`
   * is snake_cased for free while `remove` holds keys as array *values* and has to be converted
   * here - it would otherwise name a key the stored blob does not have, and delete nothing.
   *
   * @param patch - the changed keys only
   * @param remove - keys to delete outright, for a migration that retires one
   */
  const patchFrontendSettings = async (patch: FrontendSettingsPayload, remove: string[] = []): Promise<void> => {
    await api.patch<boolean>('/settings/frontend', remove.length > 0
      ? { patch, remove: remove.map(key => transformCase(key, false)) }
      : { patch });
  };

  /**
   * Reads the frontend settings blob from its own resource.
   *
   * @remarks
   * Real JSON, so the shared response transformer camelCases it like any other payload and there is
   * no second decode. The blob is absent from `/settings`, which serves only what a whole-object PUT
   * can safely replace.
   */
  const getFrontendSettings = async (): Promise<Record<string, unknown>> =>
    api.get<Record<string, unknown>>('/settings/frontend', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

  const getSettings = async (): Promise<UserSettingsModel> => {
    const [response, frontendSettings] = await Promise.all([
      api.get<UserSettingsModel>('/settings', {
        skipCamelCaseKeys: CHAIN_KEYED_SETTINGS,
        validStatuses: VALID_WITH_SESSION_STATUS,
      }),
      getFrontendSettings(),
    ]);

    return UserSettingsModel.parse({ ...response, frontendSettings });
  };

  const getRawSettings = async (): Promise<SettingsUpdate> => api.get<SettingsUpdate>('/settings', {
    skipCamelCaseKeys: CHAIN_KEYED_SETTINGS,
    validStatuses: VALID_WITH_SESSION_STATUS,
  });

  const backendSettings = async (): Promise<BackendConfiguration> => {
    const response = await api.get<BackendConfiguration>('/settings/configuration');
    return BackendConfiguration.parse(response);
  };

  const updateBackendConfiguration = async (loglevel: string): Promise<BackendConfiguration> => {
    const response = await api.put<BackendConfiguration>(
      '/settings/configuration',
      { loglevel: loglevel.toUpperCase() },
    );
    return BackendConfiguration.parse(response);
  };

  const colibriSettings = async (): Promise<ColibriConfiguration> => {
    const response = await api.get<ColibriConfiguration>(
      '/settings/configuration',
      { target: RequestTarget.COLIBRI },
    );
    return ColibriConfiguration.parse(response);
  };

  const updateColibriConfiguration = async (loglevel: string): Promise<ColibriConfiguration> => {
    const response = await api.put<ColibriConfiguration>(
      '/settings/configuration',
      { loglevel: loglevel.toUpperCase() },
      { target: RequestTarget.COLIBRI },
    );
    return ColibriConfiguration.parse(response);
  };

  return {
    backendSettings,
    colibriSettings,
    getFrontendSettings,
    getRawSettings,
    getSettings,
    patchFrontendSettings,
    setSettings,
    updateBackendConfiguration,
    updateColibriConfiguration,
  };
}
