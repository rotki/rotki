import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useSessionAuthStore } from '@/modules/session/use-session-auth-store';

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
