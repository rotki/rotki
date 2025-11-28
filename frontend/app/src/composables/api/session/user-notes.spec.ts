import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useUserNotesApi } from './user-notes';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/session/user-notes', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useUserNotesApi', () => {
    describe('fetchUserNotes', () => {
      it('sends POST request with snake_case payload and returns collection', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/notes`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    identifier: 1,
                    title: 'Note 1',
                    content: 'Content of note 1',
                    location: 'DASHBOARD',
                    last_update_timestamp: 1700000000,
                    is_pinned: true,
                  },
                  {
                    identifier: 2,
                    title: 'Note 2',
                    content: 'Content of note 2',
                    location: 'DASHBOARD',
                    last_update_timestamp: 1700001000,
                    is_pinned: false,
                  },
                ],
                entries_found: 2,
                entries_limit: 10,
                entries_total: 2,
              },
              message: '',
            });
          }),
        );

        const { fetchUserNotes } = useUserNotesApi();
        const result = await fetchUserNotes({
          titleSubstring: 'Note',
          location: 'DASHBOARD',
          limit: 10,
          offset: 0,
        });

        expect(capturedBody).toEqual({
          title_substring: 'Note',
          location: 'DASHBOARD',
          limit: 10,
          offset: 0,
        });

        expect(result.data).toHaveLength(2);
        expect(result.data[0].title).toBe('Note 1');
        expect(result.data[0].isPinned).toBe(true);
        expect(result.data[1].lastUpdateTimestamp).toBe(1700001000);
      });

      it('returns empty collection when no notes exist', async () => {
        server.use(
          http.post(`${backendUrl}/api/1/notes`, () =>
            HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: 10,
                entries_total: 0,
              },
              message: '',
            })),
        );

        const { fetchUserNotes } = useUserNotesApi();
        const result = await fetchUserNotes({
          titleSubstring: '',
          location: 'G',
          limit: 10,
          offset: 0,
        });

        expect(result.data).toHaveLength(0);
        expect(result.total).toBe(0);
      });
    });

    describe('addUserNote', () => {
      it('sends PUT request with snake_case payload and returns identifier', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/notes`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: 42,
              message: '',
            });
          }),
        );

        const { addUserNote } = useUserNotesApi();
        const result = await addUserNote({
          title: 'New Note',
          content: 'Note content',
          location: 'HISTORY',
          isPinned: false,
        });

        expect(capturedBody).toEqual({
          title: 'New Note',
          content: 'Note content',
          location: 'HISTORY',
          is_pinned: false,
        });

        expect(result).toBe(42);
      });
    });

    describe('updateUserNote', () => {
      it('sends PATCH request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/notes`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { updateUserNote } = useUserNotesApi();
        const result = await updateUserNote({
          identifier: 42,
          title: 'Updated Note',
          content: 'Updated content',
          isPinned: true,
        });

        expect(capturedBody).toEqual({
          identifier: 42,
          title: 'Updated Note',
          content: 'Updated content',
          is_pinned: true,
        });

        expect(result).toBe(true);
      });

      it('throws error on failure', async () => {
        server.use(
          http.patch(`${backendUrl}/api/1/notes`, () =>
            HttpResponse.json({
              result: null,
              message: 'Note not found',
            })),
        );

        const { updateUserNote } = useUserNotesApi();

        await expect(updateUserNote({
          identifier: 999,
          title: 'Invalid',
        }))
          .rejects
          .toThrow('Note not found');
      });
    });

    describe('deleteUserNote', () => {
      it('sends DELETE request with identifier in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/notes`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { deleteUserNote } = useUserNotesApi();
        const result = await deleteUserNote(42);

        expect(capturedBody).toEqual({ identifier: 42 });
        expect(result).toBe(true);
      });

      it('throws error when note does not exist', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/notes`, () =>
            HttpResponse.json({
              result: null,
              message: 'Note not found',
            })),
        );

        const { deleteUserNote } = useUserNotesApi();

        await expect(deleteUserNote(999))
          .rejects
          .toThrow('Note not found');
      });
    });
  });
});
