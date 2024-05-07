import {
  type Notification,
  NotificationCategory,
  Severity,
} from '@rotki/common/lib/messages';
import { type MaybeRef, useSessionStorage } from '@vueuse/core';
import type { MigratedAddresses } from '@/types/websocket-messages';

function setupMigrationSessionCache(username: string): Ref<MigratedAddresses> {
  return useSessionStorage(`rotki.migrated_addresses.${username}`, []);
}

export const useAccountMigrationStore = defineStore(
  'blockchain/accounts/migration',
  () => {
    let migratedAddresses: Ref<MigratedAddresses> = ref([]);

    const { canRequestData } = storeToRefs(useSessionAuthStore());
    const { txChains, getChainName, isEvm } = useSupportedChains();
    const { fetchAccounts } = useBlockchains();

    const { t } = useI18n();
    const { notify } = useNotificationsStore();

    const handleMigratedAccounts = (): void => {
      const txEvmChainsVal = get(txChains);
      assert(txEvmChainsVal.length > 0, 'Supported chains is empty');
      const tokenChains: string[] = txEvmChainsVal.map(x => x.id);
      const addresses: Record<string, string[]> = {};
      const migrated: MigratedAddresses | null = get(migratedAddresses);

      if (migrated === null || migrated.length === 0)
        return;

      migrated.forEach(({ address, chain }) => {
        if (tokenChains.includes(chain)) {
          if (!addresses[chain])
            addresses[chain] = [];

          addresses[chain].push(address);
        }
      });

      const promises: Promise<void>[] = [];
      const notifications: Notification[] = [];
      for (const chain in addresses) {
        const chainAddresses = addresses[chain];
        const chainName = get(getChainName(chain));
        promises.push(fetchAccounts(chain));
        if (get(isEvm(chain)))
          promises.push(useTokenDetection(chain).detectTokens(chainAddresses));

        notifications.push({
          title: t(
            'notification_messages.address_migration.title',
            { chain: chainName },
            chainAddresses.length,
          ),
          message: t(
            'notification_messages.address_migration.message',
            {
              chain: chainName,
              addresses: chainAddresses.join(', '),
            },
            chainAddresses.length,
          ),
          severity: Severity.INFO,
          display: true,
          category: NotificationCategory.ADDRESS_MIGRATION,
          duration: -1,
        });
      }

      startPromise(Promise.allSettled(promises));
      set(migratedAddresses, []);

      notifications.forEach(notify);
    };

    const runMigrationIfPossible = (canRequestData: MaybeRef<boolean>) => {
      const migrated = get(migratedAddresses);
      if (get(canRequestData) && migrated.length > 0)
        handleMigratedAccounts();
    };

    const upgradeMigratedAddresses = (data: MigratedAddresses): void => {
      set(migratedAddresses, data);
      runMigrationIfPossible(canRequestData);
    };

    const setupCache = (username: string): void => {
      migratedAddresses = setupMigrationSessionCache(username);
    };

    watch(canRequestData, runMigrationIfPossible);

    return {
      migratedAddresses,
      setupCache,
      setUpgradedAddresses: upgradeMigratedAddresses,
    };
  },
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountMigrationStore, import.meta.hot),
  );
}
