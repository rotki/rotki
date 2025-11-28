import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HTTPStatus } from '@/types/api/http';
import { useCalendarReminderApi } from './reminder';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/history/calendar/reminder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCalendarReminderApi', () => {
    describe('fetchCalendarReminders', () => {
      it('sends POST request with snake_case payload and returns entries', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/calendar/reminders`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    identifier: 1,
                    event_id: 10,
                    secs_before: 3600,
                    acknowledged: false,
                  },
                  {
                    identifier: 2,
                    event_id: 10,
                    secs_before: 86400,
                    acknowledged: true,
                  },
                ],
              },
              message: '',
            });
          }),
        );

        const { fetchCalendarReminders } = useCalendarReminderApi();
        const result = await fetchCalendarReminders({ identifier: 10 });

        expect(capturedBody).toEqual({ identifier: 10 });
        expect(result).toHaveLength(2);
        expect(result[0].identifier).toBe(1);
        expect(result[0].eventId).toBe(10);
        expect(result[0].secsBefore).toBe(3600);
      });
    });

    describe('addCalendarReminder', () => {
      it('sends PUT request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/calendar/reminders`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: { success: [1, 2] },
              message: '',
            });
          }),
        );

        const { addCalendarReminder } = useCalendarReminderApi();
        const result = await addCalendarReminder([
          { eventId: 10, secsBefore: 3600 },
          { eventId: 10, secsBefore: 86400 },
        ]);

        expect(capturedBody).toEqual({
          reminders: [
            { event_id: 10, secs_before: 3600 },
            { event_id: 10, secs_before: 86400 },
          ],
        });

        expect(result.success).toEqual([1, 2]);
      });
    });

    describe('editCalendarReminder', () => {
      it('sends PATCH request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/calendar/reminders`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: { entry_id: 1 },
              message: '',
            });
          }),
        );

        const { editCalendarReminder } = useCalendarReminderApi();
        const result = await editCalendarReminder({
          identifier: 1,
          eventId: 10,
          secsBefore: 7200,
          acknowledged: false,
        });

        expect(capturedBody).toEqual({
          identifier: 1,
          event_id: 10,
          secs_before: 7200,
          acknowledged: false,
        });

        expect(result.entryId).toBe(1);
      });
    });

    describe('deleteCalendarReminder', () => {
      it('sends DELETE request with identifier in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/calendar/reminders`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { deleteCalendarReminder } = useCalendarReminderApi();
        const result = await deleteCalendarReminder(1);

        expect(capturedBody).toEqual({ identifier: 1 });
        expect(result).toBe(true);
      });

      it('throws error on failure', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/calendar/reminders`, () =>
            HttpResponse.json({
              result: null,
              message: 'Reminder not found',
            }, { status: HTTPStatus.BAD_REQUEST })),
        );

        const { deleteCalendarReminder } = useCalendarReminderApi();

        await expect(deleteCalendarReminder(999))
          .rejects
          .toThrow();
      });
    });
  });
});
