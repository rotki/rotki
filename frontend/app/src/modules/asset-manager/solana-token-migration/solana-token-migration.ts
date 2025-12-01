import { api } from '@/modules/api/rotki-api';

interface SolanaTokenMigrationPayload {
  asyncQuery?: boolean;
  oldAsset: string;
  address: string;
  decimals: number;
  tokenKind: string;
}

interface UseSolanaTokenMigrationApiReturn {
  migrateSolanaToken: (payload: SolanaTokenMigrationPayload) => Promise<boolean>;
}

export function useSolanaTokenMigrationApi(): UseSolanaTokenMigrationApiReturn {
  const migrateSolanaToken = async (payload: SolanaTokenMigrationPayload): Promise<boolean> => api.post<boolean>(
    '/solana/tokens/migrate',
    {
      address: payload.address,
      asyncQuery: payload.asyncQuery ?? false,
      decimals: payload.decimals,
      oldAsset: payload.oldAsset,
      tokenKind: payload.tokenKind,
    },
  );

  return {
    migrateSolanaToken,
  };
}
