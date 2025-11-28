import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useMoneriumOAuthApi } from './use-monerium-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/external-services/monerium/use-monerium-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useMoneriumOAuthApi', () => {
    describe('getStatus', () => {
      it('sends GET request and returns status', async () => {
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

      it('returns unauthenticated status', async () => {
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
      it('sends PUT request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/services/monerium`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                success: true,
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
      it('sends DELETE request and returns success', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/services/monerium`, () =>
            HttpResponse.json({
              result: { success: true },
              message: '',
            })),
        );

        const { disconnect } = useMoneriumOAuthApi();
        const result = await disconnect();

        expect(result.success).toBe(true);
      });

      it('returns failure on error', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/services/monerium`, () =>
            HttpResponse.json({
              result: { success: false },
              message: 'Disconnect failed',
            })),
        );

        const { disconnect } = useMoneriumOAuthApi();
        const result = await disconnect();

        expect(result.success).toBe(false);
      });
    });
  });
});
