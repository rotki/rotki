import { type Ref } from 'vue';
import {
  type Notification,
  NotificationCategory,
  Severity
} from '@rotki/common/lib/messages';
import { type MigratedAddresses } from '@/types/websocket-messages';
import { useSessionAuthStore } from '@/store/session/auth';
import { startPromise } from '@/utils';
import { useNotificationsStore } from '@/store/notifications';

export const useAccountMigrationStore = defineStore(
  'blockchain/accounts/migration',
  () => {
    const migratedAddresses: Ref<MigratedAddresses | null> = ref(null);

    const { logged } = storeToRefs(useSessionAuthStore());
    const { txEvmChains, getChain } = useSupportedChains();

    const { tc } = useI18n();

    const upgradeMigratedAddresses = (
      data: MigratedAddresses | null = null
    ) => {
      set(migratedAddresses, data);
      checkLoggedStatus(get(logged));
    };

    const handleMigratedAccounts = () => {
      const tokenChains = get(txEvmChains).map(x => x.evmChainName);
      const addresses: Record<string, string[]> = {};
      const migrated = get(migratedAddresses);

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
      set(migratedAddresses, null);

      notifications.forEach(useNotificationsStore().notify);
    };

    const checkLoggedStatus = (logged: boolean) => {
      const migrated = get(migratedAddresses);
      if (logged && migrated !== null) {
        handleMigratedAccounts();
      }
    };

    watch(logged, logged => {
      checkLoggedStatus(logged);
    });

    return {
      migratedAddresses,
      upgradeMigratedAddresses
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAccountMigrationStore, import.meta.hot)
  );
}
