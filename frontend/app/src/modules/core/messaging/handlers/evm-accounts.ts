import type { StateHandler } from '../interfaces';
import { useAccountMigration } from '@/modules/accounts/use-account-migration';
import { createStateHandler } from '@/modules/core/messaging/utils';

export function createEvmAccountsHandler(): StateHandler {
  // Capture composable method at handler creation time (in setup context)
  const { setUpgradedAddresses } = useAccountMigration();

  return createStateHandler((data) => {
    setUpgradedAddresses(data);
  });
}
