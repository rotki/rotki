import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HTTPStatus } from '@/types/api/http';
import { useSolanaTokenMigrationApi } from './solana-token-migration';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/asset-manager/solana-token-migration/solana-token-migration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useSolanaTokenMigrationApi', () => {
    describe('migrateSolanaToken', () => {
      it('sends POST request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/solana/tokens/migrate`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { migrateSolanaToken } = useSolanaTokenMigrationApi();
        const result = await migrateSolanaToken({
          oldAsset: 'old-token-id',
          address: 'SoLaNaAdDrEsS123',
          decimals: 9,
          tokenKind: 'SPL',
        });

        expect(capturedBody).toEqual({
          old_asset: 'old-token-id',
          address: 'SoLaNaAdDrEsS123',
          decimals: 9,
          token_kind: 'SPL',
          async_query: false,
        });

        expect(result).toBe(true);
      });

      it('sends async_query true when specified', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/solana/tokens/migrate`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { migrateSolanaToken } = useSolanaTokenMigrationApi();
        await migrateSolanaToken({
          oldAsset: 'old-token-id',
          address: 'SoLaNaAdDrEsS123',
          decimals: 9,
          tokenKind: 'SPL',
          asyncQuery: true,
        });

        expect(capturedBody).toEqual({
          old_asset: 'old-token-id',
          address: 'SoLaNaAdDrEsS123',
          decimals: 9,
          token_kind: 'SPL',
          async_query: true,
        });
      });

      it('throws error on failure', async () => {
        server.use(
          http.post(`${backendUrl}/api/1/solana/tokens/migrate`, () =>
            HttpResponse.json({
              result: null,
              message: 'Migration failed',
            }, { status: HTTPStatus.BAD_REQUEST })),
        );

        const { migrateSolanaToken } = useSolanaTokenMigrationApi();

        await expect(migrateSolanaToken({
          oldAsset: 'invalid-token',
          address: 'invalid-address',
          decimals: 9,
          tokenKind: 'SPL',
        }))
          .rejects
          .toThrow();
      });
    });
  });
});
