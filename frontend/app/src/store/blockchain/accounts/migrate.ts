import type { MigratedAddresses } from '@/types/websocket-messages';
import { useTokenDetection } from '@/composables/balances/token-detection';
import { useBlockchains } from '@/composables/blockchain';
import { useSupportedChains } from '@/composables/info/chains';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionAuthStore } from '@/store/session/auth';
import { type Notification, NotificationCategory, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { type MaybeRef, useSessionStorage } from '@vueuse/core';

function setupMigrationSessionCache(identifier: string): Ref<MigratedAddresses> {
  return useSessionStorage(`rotki.migrated_addresses.${identifier}`, []);
}

export const useAccountMigrationStore = defineStore('blockchain/accounts/migration', () => {
  let migratedAddresses = ref<MigratedAddresses>([]);

  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { getChainName, isEvm, txChains } = useSupportedChains();
  const { fetchAccounts } = useBlockchains();
  const loggedUserIdentifier = useLoggedUserIdentifier();

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
        category: NotificationCategory.ADDRESS_MIGRATION,
        display: true,
        duration: -1,
        message: t(
          'notification_messages.address_migration.message',
          {
            addresses: chainAddresses.join(', '),
            chain: chainName,
          },
          chainAddresses.length,
        ),
        severity: Severity.INFO,
        title: t('notification_messages.address_migration.title', { chain: chainName }, chainAddresses.length),
      });
    }

    startPromise(Promise.allSettled(promises));
    set(migratedAddresses, []);

    notifications.forEach(notify);
  };

  const runMigrationIfPossible = (canRequestData: MaybeRef<boolean>): void => {
    const migrated = get(migratedAddresses);
    if (get(canRequestData) && migrated.length > 0)
      handleMigratedAccounts();
  };

  const upgradeMigratedAddresses = (data: MigratedAddresses): void => {
    set(migratedAddresses, data);
    runMigrationIfPossible(canRequestData);
  };

  watch(canRequestData, runMigrationIfPossible);

  watch(loggedUserIdentifier, (identifier) => {
    if (!identifier)
      migratedAddresses = ref<MigratedAddresses>([]);
    else
      migratedAddresses = setupMigrationSessionCache(identifier);
  }, { immediate: true });

  return {
    migratedAddresses,
    setUpgradedAddresses: upgradeMigratedAddresses,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAccountMigrationStore, import.meta.hot));
