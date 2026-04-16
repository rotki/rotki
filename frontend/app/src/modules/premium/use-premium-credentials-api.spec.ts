import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremiumCredentialsApi } from './use-premium-credentials-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/session/premium-credentials', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('setPremiumCredentials', () => {
    it('should set premium credentials', async () => {
      let capturedBody: DefaultBodyType = null;
      let capturedUsername: string | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/users/:username`, async ({ request, params }) => {
          capturedBody = await request.json();
          capturedUsername = String(params.username);
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

    it('should throw error on invalid credentials', async () => {
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
    it('should delete premium credentials', async () => {
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

    it('should throw error on failure', async () => {
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
    it('should get premium capabilities', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
          HttpResponse.json({
            result: {
              ethStakingView: { enabled: true, minimumTier: 'Lite' },
              eventAnalysisView: { enabled: true, minimumTier: 'Basic' },
              graphsView: { enabled: false, minimumTier: 'Advanced' },
            },
            message: '',
          })),
      );

      const { getPremiumCapabilities } = usePremiumCredentialsApi();
      const result = await getPremiumCapabilities();

      expect(result.ethStakingView?.enabled).toBe(true);
      expect(result.ethStakingView?.minimumTier).toBe('Lite');
      expect(result.eventAnalysisView?.enabled).toBe(true);
      expect(result.graphsView?.enabled).toBe(false);
    });

    it('should return defaults when no premium', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
          HttpResponse.json({
            result: {},
            message: '',
          })),
      );

      const { getPremiumCapabilities } = usePremiumCredentialsApi();
      const result = await getPremiumCapabilities();

      expect(result.ethStakingView?.enabled).toBeUndefined();
      expect(result.eventAnalysisView?.enabled).toBeUndefined();
      expect(result.graphsView?.enabled).toBeUndefined();
    });

    it('drops invalid keys and keeps valid ones', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/premium/capabilities`, () =>
          HttpResponse.json({
            result: {
              ethStakingView: { enabled: true, minimumTier: 'Lite' },
              graphsView: 'not-an-object',
              historyEventsLimit: 'not-a-number',
              currentTier: 'Basic',
            },
            message: '',
          })),
      );

      const { getPremiumCapabilities } = usePremiumCredentialsApi();
      const result = await getPremiumCapabilities();

      expect(result.ethStakingView?.enabled).toBe(true);
      expect(result.ethStakingView?.minimumTier).toBe('Lite');
      expect(result.currentTier).toBe('Basic');
      expect(result.graphsView).toBeUndefined();
      expect(result.historyEventsLimit).toBeUndefined();
    });

    it('should throw error on failure', async () => {
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
