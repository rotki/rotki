import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMoneriumOAuthApi } from './use-monerium-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('useMoneriumOAuthApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getStatus', () => {
    it('should send GET request and returns status', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/services/monerium`, () =>
          HttpResponse.json({
            result: {
              authenticated: true,
              user_email: 'test@example.com',
              default_profile_id: 'profile-123',
            },
            message: '',
          })),
      );

      const { getStatus } = useMoneriumOAuthApi();
      const result = await getStatus();

      expect(result.authenticated).toBe(true);
      expect(result.userEmail).toBe('test@example.com');
    });

    it('should return unauthenticated status', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/services/monerium`, () =>
          HttpResponse.json({
            result: {
              authenticated: false,
            },
            message: '',
          })),
      );

      const { getStatus } = useMoneriumOAuthApi();
      const result = await getStatus();

      expect(result.authenticated).toBe(false);
    });
  });

  describe('completeOAuth', () => {
    it('should send PUT request with snake_case payload', async () => {
      let capturedBody: unknown;

      server.use(
        http.put(`${backendUrl}/api/1/services/monerium`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              success: true,
              message: 'OAuth completed successfully',
            },
            message: '',
          });
        }),
      );

      const { completeOAuth } = useMoneriumOAuthApi();
      const result = await completeOAuth('access-token-123', 'refresh-token-456', 3600);

      expect(capturedBody).toEqual({
        access_token: 'access-token-123',
        refresh_token: 'refresh-token-456',
        expires_in: 3600,
      });

      expect(result.success).toBe(true);
    });
  });

  describe('disconnect', () => {
    it('should send DELETE request and returns success', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/services/monerium`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
      );

      const { disconnect } = useMoneriumOAuthApi();
      const result = await disconnect();

      expect(result).toBe(true);
    });

    it('should throw on error', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/services/monerium`, () =>
          HttpResponse.json({
            result: false,
            message: 'Disconnect failed',
          })),
      );

      const { disconnect } = useMoneriumOAuthApi();

      await expect(disconnect()).rejects.toThrow('Disconnect failed');
    });
  });
});
