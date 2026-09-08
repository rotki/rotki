import type { StateHandler } from '../interfaces';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { createStateHandler } from '@/modules/core/messaging/utils';

export function createDbUpgradeHandler(): StateHandler {
  const { updateDbUpgradeStatus } = useSessionAuthStore();

  return createStateHandler((data) => {
    updateDbUpgradeStatus(data);
  });
}

export function createDataMigrationHandler(): StateHandler {
  const { updateDataMigrationStatus } = useSessionAuthStore();

  return createStateHandler((data) => {
    updateDataMigrationStatus(data);
  });
}
