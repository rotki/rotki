import {
  AccountSession,
  type BasicLoginCredentials,
  type CreateAccountPayload,
  type LoginCredentials,
} from '@/modules/auth/login';
import { apiUrls } from '@/modules/core/api/api-urls';
import { api } from '@/modules/core/api/rotki-api';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { VALID_ACCOUNT_OPERATION_STATUS } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';

/**
 * The 400 body colibri answers with when it holds no unlocked user db
 * (`logout_user` in `colibri/src/api/database.rs`).
 */
const COLIBRI_ALREADY_LOCKED = 'DB not unlocked';

interface UseUsersApiReturn {
  authenticate: (credentials: BasicLoginCredentials) => Promise<void>;
  createAccount: (payload: CreateAccountPayload) => Promise<PendingTask>;
  login: (credentials: LoginCredentials) => Promise<PendingTask>;
  colibriLogin: (credentials: BasicLoginCredentials) => Promise<boolean>;
  colibriLogout: () => Promise<boolean>;
  checkIfLogged: (username: string) => Promise<boolean>;
  loggedUsers: () => Promise<string[]>;
  getUserProfiles: () => Promise<string[]>;
  logout: (username: string) => Promise<boolean>;
  changeUserPassword: (username: string, currentPassword: string, newPassword: string) => Promise<true>;
}

export function useUsersApi(): UseUsersApiReturn {
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

  /**
   * Lock colibri's copy of the user db. Treats "already locked" as success: that is
   * precisely the state this call aims for, and it is reached on every ordinary path —
   * a resumed session (page reload while logged in) never unlocks colibri at all.
   *
   * Without this, the throw stops `logout` before it reaches core — colibri is locked
   * first by design — so core keeps the session, `/users` still reports `loggedin`, and
   * the user is stuck on "Logout failed / DB not unlocked" with no way out. Any other
   * colibri failure still rejects: an account is locked only once both are locked.
   */
  const colibriLogout = async (): Promise<boolean> => {
    try {
      return await api.post<boolean>(
        '/user/logout',
        undefined,
        {
          baseURL: apiUrls.colibriApiUrl,
          validStatuses: VALID_ACCOUNT_OPERATION_STATUS,
          treat409AsSuccess: true,
        },
      );
    }
    catch (error: unknown) {
      if (error instanceof ApiValidationError && error.message === COLIBRI_ALREADY_LOCKED)
        return true;
      throw error;
    }
  };

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

  /**
   * Authenticate-first for the Docker cookie deployment: validate the password
   * and obtain the signed `rotki_session` HttpOnly cookie before the heavy async
   * unlock, so the cookie already rides the WebSocket handshake and the `/tasks`
   * poll that follow. Inert when no session key is configured (Electron uses the
   * renderer secret; dev/standalone): the backend returns success without a
   * cookie, so this is a cheap no-op. `skipAuthHandler` so a wrong-password 401 is
   * surfaced to the login flow instead of triggering the global logout handler.
   */
  const authenticate = async (credentials: BasicLoginCredentials): Promise<void> => {
    const { password, username } = credentials;
    await api.post(
      `/users/${username}/authenticate`,
      { password },
      {
        skipAuthHandler: true,
        validStatuses: VALID_ACCOUNT_OPERATION_STATUS,
      },
    );
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
    { skipAuthHandler: true },
  );

  return {
    authenticate,
    changeUserPassword,
    checkIfLogged,
    colibriLogin,
    colibriLogout,
    createAccount,
    getUserProfiles,
    loggedUsers,
    login,
    logout,
  };
}
