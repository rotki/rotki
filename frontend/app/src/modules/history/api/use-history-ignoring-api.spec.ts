import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useHistoryIgnoringApi } from '@/modules/history/api/use-history-ignoring-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/history/ignore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('ignoreActions', () => {
    it('should send PUT request with correct payload to ignore actions', async () => {
      let requestBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/actions/ignored`, async ({ request }) => {
          requestBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { ignoreActions } = useHistoryIgnoringApi();
      const payload = {
        data: ['event1', 'event2', 'event3'],
      };

      const result = await ignoreActions(payload);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        data: ['event1', 'event2', 'event3'],
      });
    });

    it('should handle single item in data array', async () => {
      let requestBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/actions/ignored`, async ({ request }) => {
          requestBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { ignoreActions } = useHistoryIgnoringApi();
      const payload = {
        data: ['single-event-id'],
      };

      const result = await ignoreActions(payload);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        data: ['single-event-id'],
      });
    });
  });

  describe('unignoreActions', () => {
    it('should send DELETE request with correct payload to unignore actions', async () => {
      let requestBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/actions/ignored`, async ({ request }) => {
          requestBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { unignoreActions } = useHistoryIgnoringApi();
      const payload = {
        data: ['event1', 'event2'],
      };

      const result = await unignoreActions(payload);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        data: ['event1', 'event2'],
      });
    });

    it('should handle single item in data array', async () => {
      let requestBody: DefaultBodyType = null;

      server.use(
        http.delete(`${backendUrl}/api/1/actions/ignored`, async ({ request }) => {
          requestBody = await request.json();
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { unignoreActions } = useHistoryIgnoringApi();
      const payload = {
        data: ['single-event-id'],
      };

      const result = await unignoreActions(payload);

      expect(result).toBe(true);
      expect(requestBody).toEqual({
        data: ['single-event-id'],
      });
    });
  });
});
