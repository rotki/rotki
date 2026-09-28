import type { StateHandler } from '@/modules/core/messaging/interfaces';
import type { SolanaTokensMigrationData } from '@/modules/core/messaging/types';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import { createStateHandler } from '@/modules/core/messaging/utils';

/**
 * Records the Solana tokens that need migrating by hand, which the action center counts.
 *
 * @remarks
 * Creates no notification. The backend sends the list once per unlock and nothing can read it again,
 * so the store is the session's only copy; migrating or merging a token takes it off.
 */
export function createSolanaTokensHandler(): StateHandler<SolanaTokensMigrationData> {
  const store = useSolanaTokenMigrationStore();

  return createStateHandler<SolanaTokensMigrationData>((data) => {
    store.setIdentifiers(data.identifiers);
  });
}
