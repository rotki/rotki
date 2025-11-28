import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremiumCredentialsApi } from './premium-credentials';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/session/premium-credentials', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('setPremiumCredentials', () => {
    it('sets premium credentials', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUsername: string | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/users/:username`, async ({ request, params }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          capturedUsername = params.username as string;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { setPremiumCredentials } = usePremiumCredentialsApi();
      const result = await setPremiumCredentials('testuser', 'api-key-123', 'api-secret-456');

      expect(capturedUsername).toBe('testuser');
      expect(capturedBody).toEqual({
        premium_api_key: 'api-key-123',
        premium_api_secret: 'api-secret-456',
      });
      expect(result).toBe(true);
    });

    it('throws error on invalid credentials', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/users/:username`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid API credentials',
          })),
      );

      const { setPremiumCredentials } = usePremiumCredentialsApi();

      await expect(setPremiumCredentials('testuser', 'bad-key', 'bad-secret'))
        .rejects
        .toThrow('Invalid API credentials');
    });
  });

  describe('deletePremiumCredentials', () => {
    it('deletes premium credentials', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/premium`, () =>
          HttpResponse.json({
            result: true,
            message: '',
          })),
      );

      const { deletePremiumCredentials } = usePremiumCredentialsApi();
      const result = await deletePremiumCredentials();

      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/premium`, () =>
          HttpResponse.json({
            result: null,
            message: 'No premium credentials to delete',
          })),
      );

      const { deletePremiumCredentials } = usePremiumCredentialsApi();

      await expect(deletePremiumCredentials())
        .rejects
        .toThrow('No premium credentials to delete');
    });
  });

  describe('getPremiumCapabilities', () => {
    it('gets premium capabilities', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
          HttpResponse.json({
            result: {
              ethStakingView: true,
              eventAnalysisView: true,
              graphsView: false,
            },
            message: '',
          })),
      );

      const { getPremiumCapabilities } = usePremiumCredentialsApi();
      const result = await getPremiumCapabilities();

      expect(result.ethStakingView).toBe(true);
      expect(result.eventAnalysisView).toBe(true);
      expect(result.graphsView).toBe(false);
    });

    it('returns defaults when no premium', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
          HttpResponse.json({
            result: {},
            message: '',
          })),
      );

      const { getPremiumCapabilities } = usePremiumCredentialsApi();
      const result = await getPremiumCapabilities();

      expect(result.ethStakingView).toBe(false);
      expect(result.eventAnalysisView).toBe(false);
      expect(result.graphsView).toBe(false);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
          HttpResponse.json({
            result: null,
            message: 'Service unavailable',
          })),
      );

      const { getPremiumCapabilities } = usePremiumCredentialsApi();

      await expect(getPremiumCapabilities())
        .rejects
        .toThrow('Service unavailable');
    });
  });
});
