import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useInfoApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/info/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('info', () => {
    it('fetches backend info without update check by default', async () => {
      let capturedParams: URLSearchParams | null = null;

      const mockInfo = {
        accept_docker_risk: false,
        backend_default_arguments: {
          max_logfiles_num: 3,
          max_size_in_mb_all_logs: 300,
          sqlite_instructions: 5000,
        },
        data_directory: '/home/user/.local/share/rotki/data',
        log_level: 'debug',
        version: {
          our_version: '1.35.0',
          latest_version: '1.35.0',
          download_url: 'https://rotki.com/download',
        },
      };

      server.use(
        http.get(`${backendUrl}/api/1/info`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: mockInfo,
            message: '',
          });
        }),
      );

      const { info } = useInfoApi();
      const result = await info();

      expect(capturedParams!.get('check_for_updates')).toBe('false');
      expect(result.acceptDockerRisk).toBe(false);
      expect(result.dataDirectory).toBe('/home/user/.local/share/rotki/data');
      expect(result.logLevel).toBe('debug');
      expect(result.version.ourVersion).toBe('1.35.0');
    });

    it('fetches backend info with update check when requested', async () => {
      let capturedParams: URLSearchParams | null = null;

      const mockInfo = {
        accept_docker_risk: true,
        backend_default_arguments: {
          max_logfiles_num: 5,
          max_size_in_mb_all_logs: 500,
          sqlite_instructions: 10000,
        },
        data_directory: '/data/rotki',
        log_level: 'info',
        version: {
          our_version: '1.34.0',
          latest_version: '1.35.0',
          download_url: 'https://rotki.com/download',
        },
      };

      server.use(
        http.get(`${backendUrl}/api/1/info`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: mockInfo,
            message: '',
          });
        }),
      );

      const { info } = useInfoApi();
      const result = await info(true);

      expect(capturedParams!.get('check_for_updates')).toBe('true');
      expect(result.acceptDockerRisk).toBe(true);
      expect(result.version.ourVersion).toBe('1.34.0');
      expect(result.version.latestVersion).toBe('1.35.0');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/info`, () =>
          HttpResponse.json({
            result: null,
            message: 'Backend unavailable',
          })),
      );

      const { info } = useInfoApi();

      await expect(info())
        .rejects
        .toThrow('Backend unavailable');
    });
  });

  describe('ping', () => {
    it('sends ping request and returns success', async () => {
      let requestMethod = '';

      server.use(
        http.get(`${backendUrl}/api/1/ping`, ({ request }) => {
          requestMethod = request.method;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { ping } = useInfoApi();
      const result = await ping();

      expect(requestMethod).toBe('GET');
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/ping`, () =>
          HttpResponse.json({
            result: null,
            message: 'Connection failed',
          })),
      );

      const { ping } = useInfoApi();

      await expect(ping())
        .rejects
        .toThrow('Connection failed');
    });
  });
});
