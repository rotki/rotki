import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useAccountMigrationStore } from '@/store/blockchain/accounts/migrate';

export function createEvmAccountsHandler(): StateHandler {
  return createStateHandler((data) => {
    const { setUpgradedAddresses } = useAccountMigrationStore();
    setUpgradedAddresses(data);
  });
}
