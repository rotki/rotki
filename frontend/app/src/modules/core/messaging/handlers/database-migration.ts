import type { StateHandler } from '../interfaces';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { createStateHandler } from '@/modules/core/messaging/utils';

export function createDbUpgradeHandler(): StateHandler {
  // Capture store methods at handler creation time (in setup context)
  const { updateDbUpgradeStatus } = useSessionAuthStore();

  return createStateHandler((data) => {
    updateDbUpgradeStatus(data);
  });
}

export function createDataMigrationHandler(): StateHandler {
  // Capture store methods at handler creation time (in setup context)
  const { updateDataMigrationStatus } = useSessionAuthStore();

  return createStateHandler((data) => {
    updateDataMigrationStatus(data);
  });
}
