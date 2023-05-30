import { type ActionResult } from '@rotki/common/lib/data';
import {
  setupTransformer,
  snakeCaseTransformer
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  validAccountOperationStatus,
  validAuthorizedStatus,
  validStatus
} from '@/services/utils';
import {
  AccountSession,
  type CreateAccountPayload,
  type LoginCredentials
} from '@/types/login';
import { type PendingTask } from '@/types/task';

export const useUsersApi = () => {
  const getUsers = async (): Promise<AccountSession> => {
    const response = await api.instance.get<ActionResult<AccountSession>>(
      `/users`,
      {
        transformResponse: setupTransformer(true)
      }
    );
    return AccountSession.parse(handleResponse(response));
  };

  const users = async (): Promise<string[]> => Object.keys(await getUsers());

  const checkIfLogged = async (username: string): Promise<boolean> =>
    (await getUsers())[username] === 'loggedin';

  const loggedUsers = async (): Promise<string[]> => {
    const result: AccountSession = await getUsers();
    const loggedUsers: string[] = [];
    for (const user in result) {
      if (result[user] !== 'loggedin') {
        continue;
      }
      loggedUsers.push(user);
    }
    return loggedUsers;
  };

  const logout = async (username: string): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/users/${username}`,
      {
        action: 'logout'
      },
      { validateStatus: validAccountOperationStatus }
    );

    const success = response.status === 409 ? true : handleResponse(response);
    api.cancel();
    return success;
  };

  const createAccount = async (
    payload: CreateAccountPayload
  ): Promise<PendingTask> => {
    const { credentials, premiumSetup } = payload;
    const { username, password } = credentials;

    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/users',
      snakeCaseTransformer({
        name: username,
        password,
        premiumApiKey: premiumSetup?.apiKey,
        premiumApiSecret: premiumSetup?.apiSecret,
        initialSettings: {
          submitUsageAnalytics: premiumSetup?.submitUsageAnalytics
        },
        syncDatabase: premiumSetup?.syncDatabase,
        asyncQuery: true
      }),
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  const login = async (credentials: LoginCredentials): Promise<PendingTask> => {
    const { username, ...otherFields } = credentials;
    const response = await api.instance.post<ActionResult<PendingTask>>(
      `/users/${username}`,
      snakeCaseTransformer({
        ...otherFields,
        asyncQuery: true
      }),
      {
        validateStatus: validAccountOperationStatus
      }
    );

    return handleResponse(response);
  };

  const changeUserPassword = async (
    username: string,
    currentPassword: string,
    newPassword: string
  ): Promise<true> => {
    const response = await api.instance.patch<ActionResult<true>>(
      `/users/${username}/password`,
      {
        name: username,
        current_password: currentPassword,
        new_password: newPassword
      },
      {
        validateStatus: validAuthorizedStatus
      }
    );

    return handleResponse(response);
  };

  return {
    createAccount,
    login,
    checkIfLogged,
    loggedUsers,
    users,
    logout,
    changeUserPassword
  };
};
