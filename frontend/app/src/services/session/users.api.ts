import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validAccountOperationStatus,
  validAuthorizedStatus,
  validStatus
} from '@/services/utils';
import {
  AccountSession,
  CreateAccountPayload,
  LoginCredentials
} from '@/types/login';
import { UserAccount } from '@/types/user';

export const useUsersApi = () => {
  const checkIfLogged = async (username: string): Promise<boolean> =>
    api.instance
      .get<ActionResult<AccountSession>>(`/users`)
      .then(handleResponse)
      .then(result => result[username] === 'loggedin');

  const loggedUsers = async (): Promise<string[]> =>
    api.instance
      .get<ActionResult<AccountSession>>(`/users`)
      .then(handleResponse)
      .then(result => {
        const loggedUsers: string[] = [];
        for (const user in result) {
          if (result[user] !== 'loggedin') {
            continue;
          }
          loggedUsers.push(user);
        }
        return loggedUsers;
      });

  const users = async (): Promise<string[]> => {
    const response = await api.instance.get<ActionResult<AccountSession>>(
      `/users`
    );
    const data = handleResponse(response);
    return Object.keys(data);
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
  ): Promise<UserAccount> => {
    const { credentials, premiumSetup } = payload;
    const { username, password } = credentials;

    const response = await api.instance.put<ActionResult<UserAccount>>(
      '/users',
      axiosSnakeCaseTransformer({
        name: username,
        password,
        premiumApiKey: premiumSetup?.apiKey,
        premiumApiSecret: premiumSetup?.apiSecret,
        initialSettings: {
          submitUsageAnalytics: premiumSetup?.submitUsageAnalytics
        },
        syncDatabase: premiumSetup?.syncDatabase
      }),
      {
        validateStatus: validStatus
      }
    );
    const account = handleResponse(response);
    return UserAccount.parse(account);
  };

  const login = async (credentials: LoginCredentials): Promise<PendingTask> => {
    const { password, syncApproval, username } = credentials;
    const response = await api.instance.post<ActionResult<PendingTask>>(
      `/users/${username}`,
      axiosSnakeCaseTransformer({
        password,
        syncApproval,
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
