import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';
import { apiUrls } from '@/services/api-urls';
import { setupTransformer, snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validAccountOperationStatus, validAuthorizedStatus, validStatus } from '@/services/utils';
import {
  AccountSession,
  type BasicLoginCredentials,
  type CreateAccountPayload,
  type LoginCredentials,
} from '@/types/login';

interface UseUserApiReturn {
  createAccount: (payload: CreateAccountPayload) => Promise<PendingTask>;
  login: (credentials: LoginCredentials) => Promise<PendingTask>;
  colibriLogin: (credentials: BasicLoginCredentials) => Promise<boolean>;
  checkIfLogged: (username: string) => Promise<boolean>;
  loggedUsers: () => Promise<string[]>;
  getUserProfiles: () => Promise<string[]>;
  logout: (username: string) => Promise<boolean>;
  changeUserPassword: (username: string, currentPassword: string, newPassword: string) => Promise<true>;
}

export function useUsersApi(): UseUserApiReturn {
  const getUsers = async (): Promise<AccountSession> => {
    const response = await api.instance.get<ActionResult<AccountSession>>(`/users`, {
      transformResponse: setupTransformer(true),
    });
    return AccountSession.parse(handleResponse(response));
  };

  const getUserProfiles = async (): Promise<string[]> => Object.keys(await getUsers());

  const checkIfLogged = async (username: string): Promise<boolean> => (await getUsers())[username] === 'loggedin';

  const loggedUsers = async (): Promise<string[]> => {
    const result: AccountSession = await getUsers();
    const loggedUsers: string[] = [];
    for (const user in result) {
      if (result[user] !== 'loggedin')
        continue;

      loggedUsers.push(user);
    }
    return loggedUsers;
  };

  const colibriLogout = async (): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/user/logout',
      undefined,
      {
        baseURL: apiUrls.colibriApiUrl,
        validateStatus: validAccountOperationStatus,
      },
    );

    return response.status === 409 ? true : handleResponse(response);
  };

  const logout = async (username: string): Promise<boolean> => {
    await colibriLogout();
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/users/${username}`,
      {
        action: 'logout',
      },
      { validateStatus: validAccountOperationStatus },
    );

    const success = response.status === 409 ? true : handleResponse(response);
    api.cancel();
    return success;
  };

  const createAccount = async (payload: CreateAccountPayload): Promise<PendingTask> => {
    const { credentials, initialSettings, premiumSetup } = payload;
    const { password, username } = credentials;

    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/users',
      snakeCaseTransformer({
        asyncQuery: true,
        initialSettings,
        name: username,
        password,
        premiumApiKey: premiumSetup?.apiKey,
        premiumApiSecret: premiumSetup?.apiSecret,
        syncDatabase: premiumSetup?.syncDatabase,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return handleResponse(response);
  };

  const login = async (credentials: LoginCredentials): Promise<PendingTask> => {
    const { username, ...otherFields } = credentials;
    const response = await api.instance.post<ActionResult<PendingTask>>(
      `/users/${username}`,
      snakeCaseTransformer({
        ...otherFields,
        asyncQuery: true,
      }),
      {
        validateStatus: validAccountOperationStatus,
      },
    );

    return handleResponse(response);
  };

  const colibriLogin = async (payload: BasicLoginCredentials): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/user',
      snakeCaseTransformer(payload),
      {
        baseURL: apiUrls.colibriApiUrl,
        validateStatus: validAccountOperationStatus,
      },
    );

    return handleResponse(response);
  };

  const changeUserPassword = async (username: string, currentPassword: string, newPassword: string): Promise<true> => {
    const response = await api.instance.patch<ActionResult<true>>(
      `/users/${username}/password`,
      {
        current_password: currentPassword,
        name: username,
        new_password: newPassword,
      },
      {
        validateStatus: validAuthorizedStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    changeUserPassword,
    checkIfLogged,
    colibriLogin,
    createAccount,
    getUserProfiles,
    loggedUsers,
    login,
    logout,
  };
}
