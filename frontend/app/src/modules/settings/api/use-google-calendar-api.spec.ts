import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGoogleCalendarApi } from './use-google-calendar-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/settings/google-calendar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getStatus', () => {
    it('should return authenticated status with user email', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/calendar/google`, () =>
          HttpResponse.json({
            result: {
              authenticated: true,
              user_email: 'user@example.com',
            },
            message: '',
          })),
      );

      const { getStatus } = useGoogleCalendarApi();
      const result = await getStatus();

      expect(result.authenticated).toBe(true);
      expect(result.userEmail).toBe('user@example.com');
    });

    it('should return unauthenticated status', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/calendar/google`, () =>
          HttpResponse.json({
            result: {
              authenticated: false,
            },
            message: '',
          })),
      );

      const { getStatus } = useGoogleCalendarApi();
      const result = await getStatus();

      expect(result.authenticated).toBe(false);
      expect(result.userEmail).toBeUndefined();
    });

    it('should throw error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/calendar/google`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to get status',
          })),
      );

      const { getStatus } = useGoogleCalendarApi();

      await expect(getStatus())
        .rejects
        .toThrow('Failed to get status');
    });
  });

  describe('completeOAuth', () => {
    it('should send PUT request with snake_case tokens', async () => {
      let capturedBody: DefaultBodyType = null;

      server.use(
        http.put(`${backendUrl}/api/1/calendar/google`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json({
            result: {
              success: true,
              message: 'Authentication successful',
              user_email: 'authenticated@example.com',
            },
            message: '',
          });
        }),
      );

      const { completeOAuth } = useGoogleCalendarApi();
      const result = await completeOAuth('access-token-123', 'refresh-token-456');

      expect(capturedBody).toEqual({
        access_token: 'access-token-123',
        refresh_token: 'refresh-token-456',
      });
      expect(result.success).toBe(true);
      expect(result.message).toBe('Authentication successful');
      expect(result.userEmail).toBe('authenticated@example.com');
    });

    it('should return failure result on auth error', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/calendar/google`, () =>
          HttpResponse.json({
            result: {
              success: false,
              message: 'Invalid tokens provided',
            },
            message: '',
          })),
      );

      const { completeOAuth } = useGoogleCalendarApi();
      const result = await completeOAuth('invalid-token', 'invalid-refresh');

      expect(result.success).toBe(false);
      expect(result.message).toBe('Invalid tokens provided');
    });
  });

  describe('syncCalendar', () => {
    it('should send POST request and returns sync results', async () => {
      let requestMethod = '';

      server.use(
        http.post(`${backendUrl}/api/1/calendar/google`, ({ request }) => {
          requestMethod = request.method;
          return HttpResponse.json({
            result: {
              calendar_id: 'calendar-id-abc',
              events_processed: 100,
              events_created: 25,
              events_updated: 10,
            },
            message: '',
          });
        }),
      );

      const { syncCalendar } = useGoogleCalendarApi();
      const result = await syncCalendar();

      expect(requestMethod).toBe('POST');
      expect(result.calendarId).toBe('calendar-id-abc');
      expect(result.eventsProcessed).toBe(100);
      expect(result.eventsCreated).toBe(25);
      expect(result.eventsUpdated).toBe(10);
    });

    it('should throw error on sync failure', async () => {
      server.use(
        http.post(`${backendUrl}/api/1/calendar/google`, () =>
          HttpResponse.json({
            result: null,
            message: 'Calendar sync failed',
          })),
      );

      const { syncCalendar } = useGoogleCalendarApi();

      await expect(syncCalendar())
        .rejects
        .toThrow('Calendar sync failed');
    });
  });

  describe('disconnect', () => {
    it('should send DELETE request and returns success', async () => {
      let requestMethod = '';

      server.use(
        http.delete(`${backendUrl}/api/1/calendar/google`, ({ request }) => {
          requestMethod = request.method;
          return HttpResponse.json({
            result: {
              success: true,
            },
            message: '',
          });
        }),
      );

      const { disconnect } = useGoogleCalendarApi();
      const result = await disconnect();

      expect(requestMethod).toBe('DELETE');
      expect(result.success).toBe(true);
    });

    it('should throw error on disconnect failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/calendar/google`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to disconnect',
          })),
      );

      const { disconnect } = useGoogleCalendarApi();

      await expect(disconnect())
        .rejects
        .toThrow('Failed to disconnect');
    });
  });
});
