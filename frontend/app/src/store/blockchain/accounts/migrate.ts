import { type Ref } from 'vue';
import {
  type Notification,
  NotificationCategory,
  Severity
} from '@rotki/common/lib/messages';
import { type MaybeRef, useSessionStorage } from '@vueuse/core';
import { type MigratedAddresses } from '@/types/websocket-messages';
import { startPromise } from '@/utils';

const setupMigrationSessionCache = (
  username: string
): Ref<MigratedAddresses> => {
  return useSessionStorage(`rotki.migrated_addresses.${username}`, []);
};

export const useAccountMigrationStore = defineStore(
  'blockchain/accounts/migration',
  () => {
    let migratedAddresses: Ref<MigratedAddresses> = ref([]);

    const { canRequestData } = storeToRefs(useSessionAuthStore());
    const { txEvmChains, getChain } = useSupportedChains();

    const { tc } = useI18n();
    const { notify } = useNotificationsStore();

    const upgradeMigratedAddresses = (data: MigratedAddresses): void => {
      set(migratedAddresses, data);
      runMigrationIfPossible(canRequestData);
    };

    const handleMigratedAccounts = (): void => {
      const tokenChains: string[] = get(txEvmChains).map(x => x.evmChainName);
      const addresses: Record<string, string[]> = {};
      const migrated: MigratedAddresses | null = get(migratedAddresses);

      if (migrated === null || migrated.length === 0) return;

      migrated.forEach(({ address, evmChain }) => {
        if (tokenChains.includes(evmChain)) {
          if (!addresses[evmChain]) {
            addresses[evmChain] = [address];
          } else {
            addresses[evmChain].push(address);
          }
        }
      });

      const promises: Promise<void>[] = [];
      const notifications: Notification[] = [];
      for (const chain in addresses) {
        const chainAddresses = addresses[chain];
        promises.push(
          useTokenDetection(getChain(chain)).detectTokens(chainAddresses)
        );
        notifications.push({
          title: tc(
            'notification_messages.address_migration.title',
            chainAddresses.length,
            {
              chain
            }
          ),
          message: tc(
            'notification_messages.address_migration.message',
            chainAddresses.length,
            {
              chain,
              addresses: chainAddresses.join(', ')
            }
          ),
          severity: Severity.INFO,
          display: true,
          category: NotificationCategory.ADDRESS_MIGRATION,
          duration: -1
        });
      }

      startPromise(Promise.allSettled(promises));
      set(migratedAddresses, []);

      notifications.forEach(notify);
    };

    const runMigrationIfPossible = (canRequestData: MaybeRef<boolean>) => {
      const migrated = get(migratedAddresses);
      if (get(canRequestData) && migrated.length > 0) {
        handleMigratedAccounts();
      }
    };

    const setupCache = (username: string): void => {
      migratedAddresses = setupMigrationSessionCache(username);
    };

    watch(canRequestData, runMigrationIfPossible);

    return {
      migratedAddresses,
      setupCache,
      setUpgradedAddresses: upgradeMigratedAddresses
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountMigrationStore, import.meta.hot)
  );
}
