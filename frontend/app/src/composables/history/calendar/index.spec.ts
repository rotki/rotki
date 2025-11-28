import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HTTPStatus } from '@/types/api/http';
import { useCalendarApi } from './index';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/history/calendar/index', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCalendarApi', () => {
    describe('fetchCalendarEvents', () => {
      it('sends POST request with snake_case payload and returns collection', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/calendar`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    identifier: 1,
                    name: 'Test Event',
                    description: 'Test Description',
                    timestamp: 1700000000,
                    auto_delete: false,
                  },
                ],
                entries_found: 1,
                entries_limit: 10,
                entries_total: 1,
              },
              message: '',
            });
          }),
        );

        const { fetchCalendarEvents } = useCalendarApi();
        const result = await fetchCalendarEvents({
          fromTimestamp: 1699900000,
          toTimestamp: 1700100000,
          limit: 10,
          offset: 0,
        });

        expect(capturedBody).toEqual({
          from_timestamp: 1699900000,
          to_timestamp: 1700100000,
          limit: 10,
          offset: 0,
        });

        expect(result.data).toHaveLength(1);
        expect(result.data[0].identifier).toBe(1);
        expect(result.data[0].name).toBe('Test Event');
        expect(result.data[0].autoDelete).toBe(false);
      });
    });

    describe('addCalendarEvent', () => {
      it('sends PUT request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/calendar`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: { entry_id: 42 },
              message: '',
            });
          }),
        );

        const { addCalendarEvent } = useCalendarApi();
        const result = await addCalendarEvent({
          name: 'New Event',
          description: 'New Description',
          timestamp: 1700000000,
          autoDelete: true,
        });

        expect(capturedBody).toEqual({
          name: 'New Event',
          description: 'New Description',
          timestamp: 1700000000,
          auto_delete: true,
        });

        expect(result.entryId).toBe(42);
      });
    });

    describe('editCalendarEvent', () => {
      it('sends PATCH request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/calendar`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: { entry_id: 42 },
              message: '',
            });
          }),
        );

        const { editCalendarEvent } = useCalendarApi();
        const result = await editCalendarEvent({
          identifier: 42,
          name: 'Updated Event',
          description: 'Updated Description',
          timestamp: 1700000000,
          autoDelete: false,
        });

        expect(capturedBody).toEqual({
          identifier: 42,
          name: 'Updated Event',
          description: 'Updated Description',
          timestamp: 1700000000,
          auto_delete: false,
        });

        expect(result.entryId).toBe(42);
      });
    });

    describe('deleteCalendarEvent', () => {
      it('sends DELETE request with identifier in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/calendar`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { deleteCalendarEvent } = useCalendarApi();
        const result = await deleteCalendarEvent(42);

        expect(capturedBody).toEqual({ identifier: 42 });
        expect(result).toBe(true);
      });

      it('throws error on failure', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/calendar`, () =>
            HttpResponse.json({
              result: null,
              message: 'Event not found',
            }, { status: HTTPStatus.BAD_REQUEST })),
        );

        const { deleteCalendarEvent } = useCalendarApi();

        await expect(deleteCalendarEvent(999))
          .rejects
          .toThrow();
      });
    });
  });
});
