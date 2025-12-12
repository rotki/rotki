import { apiUrls } from '@/modules/api/api-urls';
import { api } from '@/modules/api/rotki-api';
import { VALID_ACCOUNT_OPERATION_STATUS } from '@/modules/api/utils';
import {
  AccountSession,
  type BasicLoginCredentials,
  type CreateAccountPayload,
  type LoginCredentials,
} from '@/types/login';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

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
    const response = await api.get<AccountSession>(`/users`, {
      skipRootCamelCase: true,
    });
    return AccountSession.parse(response);
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

  const colibriLogout = async (): Promise<boolean> => api.post<boolean>(
    '/user/logout',
    undefined,
    {
      baseURL: apiUrls.colibriApiUrl,
      validStatuses: VALID_ACCOUNT_OPERATION_STATUS,
      treat409AsSuccess: true,
    },
  );

  const logout = async (username: string): Promise<boolean> => {
    await colibriLogout();
    const success = await api.patch<boolean>(
      `/users/${username}`,
      { action: 'logout' },
      {
        validStatuses: VALID_ACCOUNT_OPERATION_STATUS,
        treat409AsSuccess: true,
      },
    );
    api.cancelAllQueued();
    api.cancel();
    return success;
  };

  const createAccount = async (payload: CreateAccountPayload): Promise<PendingTask> => {
    const { credentials, initialSettings, premiumSetup } = payload;
    const { password, username } = credentials;

    const response = await api.put<PendingTask>(
      '/users',
      {
        asyncQuery: true,
        initialSettings,
        name: username,
        password,
        premiumApiKey: premiumSetup?.apiKey,
        premiumApiSecret: premiumSetup?.apiSecret,
        syncDatabase: premiumSetup?.syncDatabase,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const login = async (credentials: LoginCredentials): Promise<PendingTask> => {
    const { username, ...otherFields } = credentials;
    const response = await api.post<PendingTask>(
      `/users/${username}`,
      {
        ...otherFields,
        asyncQuery: true,
      },
      {
        validStatuses: VALID_ACCOUNT_OPERATION_STATUS,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const colibriLogin = async (payload: BasicLoginCredentials): Promise<boolean> => api.post<boolean>(
    '/user',
    payload,
    {
      baseURL: apiUrls.colibriApiUrl,
      validStatuses: VALID_ACCOUNT_OPERATION_STATUS,
    },
  );

  const changeUserPassword = async (username: string, currentPassword: string, newPassword: string): Promise<true> => api.patch<true>(
    `/users/${username}/password`,
    {
      currentPassword,
      name: username,
      newPassword,
    },
  );

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
