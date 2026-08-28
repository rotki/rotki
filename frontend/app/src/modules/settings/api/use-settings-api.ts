import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { CHAIN_KEYED_SETTINGS, RequestTarget } from '@/modules/core/api/constants';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/core/api/utils';
import { type SettingsUpdate, UserSettingsModel } from '@/modules/settings/types/user-settings';
import { BackendConfiguration, ColibriConfiguration } from '@/modules/shell/app/backend';

interface UseSettingsApiReturn {
  setSettings: (settings: SettingsUpdate) => Promise<UserSettingsModel>;
  patchFrontendSettings: (patch: FrontendSettingsPayload) => Promise<void>;
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
   * The whole point of merging on the server is that a key the running client's schema does not
   * declare cannot be preserved by the client: it has already been parsed away. Sending only the
   * changed keys leaves such a key untouched instead of overwriting it with a reduced view.
   *
   * @param patch - the changed keys only, in camelCase; the api layer snake_cases them on the way out
   */
  const patchFrontendSettings = async (patch: FrontendSettingsPayload): Promise<void> => {
    await api.patch<boolean>('/settings/frontend', { patch });
  };

  const getSettings = async (): Promise<UserSettingsModel> => {
    const response = await api.get<UserSettingsModel>('/settings', {
      skipCamelCaseKeys: CHAIN_KEYED_SETTINGS,
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return UserSettingsModel.parse(response);
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
    getRawSettings,
    getSettings,
    patchFrontendSettings,
    setSettings,
    updateBackendConfiguration,
    updateColibriConfiguration,
  };
}
