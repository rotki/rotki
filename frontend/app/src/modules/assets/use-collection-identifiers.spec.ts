import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useCollectionIdentifiers } from './use-collection-identifiers';

const colibriUrl = process.env.VITE_COLIBRI_URL;

describe('modules/assets/use-collection-identifiers', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useCollectionIdentifiers', () => {
    describe('getCollectionAssets', () => {
      it('sends GET request to colibri API with collection_id query param', async () => {
        let capturedUrl: URL | undefined;

        server.use(
          http.get(`${colibriUrl}/assets/collections`, ({ request }) => {
            capturedUrl = new URL(request.url);
            return HttpResponse.json({
              result: ['asset1', 'asset2', 'asset3'],
              message: '',
            });
          }),
        );

        const { getCollectionAssets } = useCollectionIdentifiers();
        const result = await getCollectionAssets('my-collection-id');

        expect(capturedUrl).toBeDefined();
        expect(capturedUrl!.searchParams.get('collection_id')).toBe('my-collection-id');
        expect(result).toEqual(['asset1', 'asset2', 'asset3']);
      });

      it('encodes special characters in collection_id', async () => {
        let capturedUrl: URL | undefined;

        server.use(
          http.get(`${colibriUrl}/assets/collections`, ({ request }) => {
            capturedUrl = new URL(request.url);
            return HttpResponse.json({
              result: [],
              message: '',
            });
          }),
        );

        const { getCollectionAssets } = useCollectionIdentifiers();
        await getCollectionAssets('collection/with&special=chars');

        expect(capturedUrl).toBeDefined();
        expect(capturedUrl!.searchParams.get('collection_id')).toBe('collection/with&special=chars');
      });

      it('returns empty array when no assets found', async () => {
        server.use(
          http.get(`${colibriUrl}/assets/collections`, () =>
            HttpResponse.json({
              result: [],
              message: '',
            })),
        );

        const { getCollectionAssets } = useCollectionIdentifiers();
        const result = await getCollectionAssets('empty-collection');

        expect(result).toEqual([]);
      });
    });
  });
});
