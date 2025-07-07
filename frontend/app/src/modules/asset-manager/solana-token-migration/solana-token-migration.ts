import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

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
  const migrateSolanaToken = async (payload: SolanaTokenMigrationPayload): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      '/solana/tokens/migrate',
      snakeCaseTransformer({
        address: payload.address,
        asyncQuery: payload.asyncQuery ?? false,
        decimals: payload.decimals,
        oldAsset: payload.oldAsset,
        tokenKind: payload.tokenKind,
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    migrateSolanaToken,
  };
}
