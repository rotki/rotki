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
   * `remove` is snake_cased here because the request transformer only converts object keys, not
   * array values.
   *
   * @param patch - the changed keys only
   * @param remove - keys to delete, camelCase
   */
  const patchFrontendSettings = async (patch: FrontendSettingsPayload, remove: string[] = []): Promise<void> => {
    await api.patch<boolean>('/settings/frontend', remove.length > 0
      ? { patch, remove: remove.map(key => transformCase(key, false)) }
      : { patch });
  };

  /** Reads the frontend settings, camelCased by the response transformer. */
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
