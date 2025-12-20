import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTagsApi } from './tags';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/tags', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useTagsApi', () => {
    describe('queryTags', () => {
      it('sends GET request and returns tags record', async () => {
        server.use(
          http.get(`${backendUrl}/api/1/tags`, () =>
            HttpResponse.json({
              result: {
                personal: {
                  name: 'personal',
                  description: 'Personal transactions',
                  background_color: 'FF5733',
                  foreground_color: 'FFFFFF',
                },
                business: {
                  name: 'business',
                  description: null,
                  background_color: '3357FF',
                  foreground_color: '000000',
                },
              },
              message: '',
            })),
        );

        const { queryTags } = useTagsApi();
        const result = await queryTags();

        expect(result.personal).toBeDefined();
        expect(result.personal.name).toBe('personal');
        expect(result.personal.backgroundColor).toBe('FF5733');
        expect(result.business.description).toBeNull();
      });

      it('returns empty record when no tags exist', async () => {
        server.use(
          http.get(`${backendUrl}/api/1/tags`, () =>
            HttpResponse.json({
              result: {},
              message: '',
            })),
        );

        const { queryTags } = useTagsApi();
        const result = await queryTags();

        expect(Object.keys(result)).toHaveLength(0);
      });
    });

    describe('queryAddTag', () => {
      it('sends PUT request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/tags`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                newtag: {
                  name: 'newtag',
                  description: 'A new tag',
                  background_color: 'AABBCC',
                  foreground_color: '112233',
                },
              },
              message: '',
            });
          }),
        );

        const { queryAddTag } = useTagsApi();
        const result = await queryAddTag({
          name: 'newtag',
          description: 'A new tag',
          backgroundColor: 'AABBCC',
          foregroundColor: '112233',
        });

        expect(capturedBody).toEqual({
          name: 'newtag',
          description: 'A new tag',
          background_color: 'AABBCC',
          foreground_color: '112233',
        });

        expect(result.newtag).toBeDefined();
        expect(result.newtag.backgroundColor).toBe('AABBCC');
      });
    });

    describe('queryEditTag', () => {
      it('sends PATCH request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/tags`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                updated: {
                  name: 'updated',
                  description: 'Updated description',
                  background_color: 'DDEEFF',
                  foreground_color: '445566',
                },
              },
              message: '',
            });
          }),
        );

        const { queryEditTag } = useTagsApi();
        const result = await queryEditTag({
          name: 'updated',
          description: 'Updated description',
          backgroundColor: 'DDEEFF',
          foregroundColor: '445566',
        }, 'updated');

        expect(capturedBody).toEqual({
          name: 'updated',
          description: 'Updated description',
          background_color: 'DDEEFF',
          foreground_color: '445566',
        });

        expect(result.updated.description).toBe('Updated description');
      });
    });

    describe('queryDeleteTag', () => {
      it('sends DELETE request with name in body', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/tags`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {},
              message: '',
            });
          }),
        );

        const { queryDeleteTag } = useTagsApi();
        const result = await queryDeleteTag('tagToDelete');

        expect(capturedBody).toEqual({ name: 'tagToDelete' });
        expect(Object.keys(result)).toHaveLength(0);
      });

      it('returns remaining tags after deletion', async () => {
        server.use(
          http.delete(`${backendUrl}/api/1/tags`, () =>
            HttpResponse.json({
              result: {
                remaining: {
                  name: 'remaining',
                  description: 'Still here',
                  background_color: 'FFFFFF',
                  foreground_color: '000000',
                },
              },
              message: '',
            })),
        );

        const { queryDeleteTag } = useTagsApi();
        const result = await queryDeleteTag('deleted');

        expect(result.remaining).toBeDefined();
        expect(result.remaining.name).toBe('remaining');
      });
    });
  });
});
