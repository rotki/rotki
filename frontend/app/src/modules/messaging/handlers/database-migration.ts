import type { StateHandler } from '../interfaces';
import { createStateHandler } from '@/modules/messaging/utils';
import { useSessionAuthStore } from '@/store/session/auth';

export function createDbUpgradeHandler(): StateHandler {
  return createStateHandler((data) => {
    const { updateDbUpgradeStatus } = useSessionAuthStore();
    updateDbUpgradeStatus(data);
  });
}

export function createDataMigrationHandler(): StateHandler {
  return createStateHandler((data) => {
    const { updateDataMigrationStatus } = useSessionAuthStore();
    updateDataMigrationStatus(data);
  });
}
