import { beforeEach, describe, expect, it } from 'vitest';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import { createSolanaTokensHandler } from './solana-tokens-migration-handler';

describe('modules/assets/admin/solana-token-migration/solana-tokens-migration-handler', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should record the tokens to migrate, which the action center counts, and post no notification', async () => {
    const handler = createSolanaTokensHandler();

    const result = await handler.handle({ identifiers: ['BONK', 'JUP'] });

    expect(useSolanaTokenMigrationStore().identifiers).toEqual(['BONK', 'JUP']);
    expect(result).toBeUndefined();
  });
});
