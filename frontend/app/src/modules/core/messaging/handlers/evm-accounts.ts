import type { StateHandler } from '../interfaces';
import { useAccountMigration } from '@/modules/accounts/use-account-migration';
import { createStateHandler } from '@/modules/core/messaging/utils';

export function createEvmAccountsHandler(): StateHandler {
  const { setUpgradedAddresses } = useAccountMigration();

  return createStateHandler((data) => {
    setUpgradedAddresses(data);
  });
}
