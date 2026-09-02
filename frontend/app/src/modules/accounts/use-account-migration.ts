import type { MaybeRef } from 'vue';
import type { MigratedAddresses } from '@/modules/core/messaging/types';
import { assert, type Notification, NotificationCategory, Severity } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { useSessionStorage } from '@vueuse/core';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useLoggedUserIdentifier } from '@/modules/auth/use-logged-user-identifier';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

function setupMigrationSessionCache(identifier: string): Ref<MigratedAddresses> {
  return useSessionStorage(`rotki.migrated_addresses.${identifier}`, []);
}

interface UseAccountMigrationReturn {
  setUpgradedAddresses: (data: MigratedAddresses) => void;
}

export function useAccountMigration(): UseAccountMigrationReturn {
  let migratedAddresses = ref<MigratedAddresses>([]);

  const { canRequestData } = storeToRefs(useSessionAuthStore());
  const { evmAndEvmLikeTxChainsInfo, getChainName, isEvm } = useSupportedChains();
  const { fetchAccounts } = useBlockchainAccountManagement();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const loggedUserIdentifier = useLoggedUserIdentifier();

  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotifications();

  function handleMigratedAccounts(): void {
    const txEvmChainsVal = get(evmAndEvmLikeTxChainsInfo);
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

    /**
     * Reads the accounts for a chain, then queries the balances of the addresses migrated onto it.
     *
     * @remarks
     * A migrated address is new to this chain, so nothing about it is in the balance cache and a
     * cache-only read cannot fetch it. Detection has to run before the query, the same order an
     * addition needs and for the same reason.
     */
    const detectThenQuery = async (chain: string, chainAddresses: string[]): Promise<void> => {
      await fetchAccounts({ blockchain: chain });
      await refreshBlockchainBalances(
        { blockchain: chain },
        RefreshMode.BACKGROUND,
        isEvm(chain) ? { detect: true, detectAddresses: chainAddresses } : {},
      );
    };

    const promises: Promise<void>[] = [];
    const notifications: Notification[] = [];
    for (const chain in addresses) {
      const chainAddresses = addresses[chain];
      const chainName = getChainName(chain);
      promises.push(detectThenQuery(chain, chainAddresses));

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
  }

  function runMigrationIfPossible(canRequest: MaybeRef<boolean>): void {
    const migrated = get(migratedAddresses);
    if (get(canRequest) && migrated.length > 0)
      handleMigratedAccounts();
  }

  function setUpgradedAddresses(data: MigratedAddresses): void {
    set(migratedAddresses, data);
    runMigrationIfPossible(canRequestData);
  }

  watch(canRequestData, runMigrationIfPossible);

  watch(loggedUserIdentifier, (identifier) => {
    if (!identifier)
      migratedAddresses = ref<MigratedAddresses>([]);
    else
      migratedAddresses = setupMigrationSessionCache(identifier);
  }, { immediate: true });

  return {
    setUpgradedAddresses,
  };
}
