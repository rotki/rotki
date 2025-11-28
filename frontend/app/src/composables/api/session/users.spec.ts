import type { CreateAccountPayload, LoginCredentials } from '@/types/login';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useUsersApi } from './users';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = process.env.VITE_COLIBRI_URL;

describe('composables/api/session/users', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getUserProfiles', () => {
    it('returns list of user profile names', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/users`, () =>
          HttpResponse.json({
            result: {
              user1: 'loggedin',
              user2: 'loggedout',
              user3: 'loggedout',
            },
            message: '',
          })),
      );

      const { getUserProfiles } = useUsersApi();
      const result = await getUserProfiles();

      expect(result).toEqual(['user1', 'user2', 'user3']);
    });
  });

  describe('checkIfLogged', () => {
    it('returns true when user is logged in', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/users`, () =>
          HttpResponse.json({
            result: {
              testuser: 'loggedin',
              otheruser: 'loggedout',
            },
            message: '',
          })),
      );

      const { checkIfLogged } = useUsersApi();
      const result = await checkIfLogged('testuser');

      expect(result).toBe(true);
    });

    it('returns false when user is logged out', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/users`, () =>
          HttpResponse.json({
            result: {
              testuser: 'loggedout',
            },
            message: '',
          })),
      );

      const { checkIfLogged } = useUsersApi();
      const result = await checkIfLogged('testuser');

      expect(result).toBe(false);
    });
  });

  describe('loggedUsers', () => {
    it('returns only logged in users', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/users`, () =>
          HttpResponse.json({
            result: {
              user1: 'loggedin',
              user2: 'loggedout',
              user3: 'loggedin',
              user4: 'loggedout',
            },
            message: '',
          })),
      );

      const { loggedUsers } = useUsersApi();
      const result = await loggedUsers();

      expect(result).toEqual(['user1', 'user3']);
    });

    it('returns empty array when no users are logged in', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/users`, () =>
          HttpResponse.json({
            result: {
              user1: 'loggedout',
              user2: 'loggedout',
            },
            message: '',
          })),
      );

      const { loggedUsers } = useUsersApi();
      const result = await loggedUsers();

      expect(result).toEqual([]);
    });
  });

  describe('createAccount', () => {
    it('sends PUT request with snake_case payload for basic account creation', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/users`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 123,
            },
            message: '',
          });
        }),
      );

      const { createAccount } = useUsersApi();
      const payload: CreateAccountPayload = {
        credentials: {
          username: 'newuser',
          password: 'securepassword123',
        },
        initialSettings: {
          submitUsageAnalytics: true,
        },
      };

      const result = await createAccount(payload);

      expect(result.taskId).toBe(123);
      expect(capturedBody).toEqual({
        async_query: true,
        initial_settings: {
          submit_usage_analytics: true,
        },
        name: 'newuser',
        password: 'securepassword123',
      });
    });

    it('sends PUT request with premium setup when provided', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/users`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 456,
            },
            message: '',
          });
        }),
      );

      const { createAccount } = useUsersApi();
      const payload: CreateAccountPayload = {
        credentials: {
          username: 'premiumuser',
          password: 'password123',
        },
        initialSettings: {
          submitUsageAnalytics: false,
        },
        premiumSetup: {
          apiKey: 'premium-api-key',
          apiSecret: 'premium-api-secret',
          syncDatabase: true,
        },
      };

      const result = await createAccount(payload);

      expect(result.taskId).toBe(456);
      expect(capturedBody).toEqual({
        async_query: true,
        initial_settings: {
          submit_usage_analytics: false,
        },
        name: 'premiumuser',
        password: 'password123',
        premium_api_key: 'premium-api-key',
        premium_api_secret: 'premium-api-secret',
        sync_database: true,
      });
    });
  });

  describe('login', () => {
    it('sends POST request with snake_case credentials', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.post(`${backendUrl}/api/1/users/:username`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 789,
            },
            message: '',
          });
        }),
      );

      const { login } = useUsersApi();
      const credentials: LoginCredentials = {
        username: 'testuser',
        password: 'mypassword',
        syncApproval: 'yes',
        resumeFromBackup: false,
      };

      const result = await login(credentials);

      expect(result.taskId).toBe(789);
      expect(capturedUrl).toContain('/users/testuser');
      expect(capturedBody).toEqual({
        password: 'mypassword',
        sync_approval: 'yes',
        resume_from_backup: false,
        async_query: true,
      });
    });

    it('sends POST request with minimal credentials', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/users/:username`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              task_id: 101,
            },
            message: '',
          });
        }),
      );

      const { login } = useUsersApi();
      const credentials: LoginCredentials = {
        username: 'minimaluser',
        password: 'pass',
      };

      const result = await login(credentials);

      expect(result.taskId).toBe(101);
      expect(capturedBody).toEqual({
        password: 'pass',
        async_query: true,
      });
    });
  });

  describe('colibriLogin', () => {
    it('sends POST request to colibri API with snake_case payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      // Note: colibri endpoints use baseURL override, so no /api/1 prefix
      server.use(
        http.post(`${colibriUrl}/user`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { colibriLogin } = useUsersApi();
      const result = await colibriLogin({
        username: 'colibriuser',
        password: 'colibripass',
      });

      expect(result).toBe(true);
      expect(capturedBody).toEqual({
        username: 'colibriuser',
        password: 'colibripass',
      });
    });
  });

  describe('logout', () => {
    it('sends PATCH request with logout action', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      // Note: colibri logout uses baseURL override, so no /api/1 prefix
      server.use(
        http.post(`${colibriUrl}/user/logout`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
        http.patch(`${backendUrl}/api/1/users/:username`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { logout } = useUsersApi();
      const result = await logout('testuser');

      expect(result).toBe(true);
      expect(capturedUrl).toContain('/users/testuser');
      expect(capturedBody).toEqual({
        action: 'logout',
      });
    });

    it('returns true when logout returns 409 conflict', async () => {
      // Note: colibri logout uses baseURL override, so no /api/1 prefix
      server.use(
        http.post(`${colibriUrl}/user/logout`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
        http.patch(`${backendUrl}/api/1/users/:username`, () =>
          HttpResponse.json({
            result: false,
            message: 'Already logged out',
          }, { status: 409 })),
      );

      const { logout } = useUsersApi();
      const result = await logout('testuser');

      expect(result).toBe(true);
    });
  });

  describe('changeUserPassword', () => {
    it('sends PATCH request with password change payload', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.patch(`${backendUrl}/api/1/users/:username/password`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { changeUserPassword } = useUsersApi();
      const result = await changeUserPassword('testuser', 'oldpassword', 'newpassword');

      expect(result).toBe(true);
      expect(capturedUrl).toContain('/users/testuser/password');
      expect(capturedBody).toEqual({
        current_password: 'oldpassword',
        name: 'testuser',
        new_password: 'newpassword',
      });
    });

    it('throws error on authentication failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/users/:username/password`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid current password',
          })),
      );

      const { changeUserPassword } = useUsersApi();

      await expect(changeUserPassword('testuser', 'wrongpassword', 'newpassword'))
        .rejects
        .toThrow('Invalid current password');
    });
  });
});
