import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useAccountMigrationStore } from '@/store/blockchain/accounts/migrate';

export function createEvmAccountsHandler(): StateHandler {
  // Capture store method at handler creation time (in setup context)
  const { setUpgradedAddresses } = useAccountMigrationStore();

  return createStateHandler((data) => {
    setUpgradedAddresses(data);
  });
}
