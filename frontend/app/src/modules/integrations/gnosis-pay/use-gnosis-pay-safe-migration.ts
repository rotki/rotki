import type { ComputedRef, Ref } from 'vue';
import type { GnosisPayUntrackedSafe } from '@/modules/integrations/gnosis-pay/types';
import { type Account, Blockchain } from '@rotki/common';
import { pipe } from 'plainfp';
import { getOr } from 'plainfp/option';
import { flatMap, fromAsync, match } from 'plainfp/result-async';
import { msg } from '@/message-key';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { findUntrackedSafe, readSafeAddition } from '@/modules/integrations/gnosis-pay/core/safe-migration';
import { useGnosisPaySiweApi } from '@/modules/integrations/gnosis-pay/use-gnosis-pay-api';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';

const GNOSIS_PAY_SERVICE = 'gnosis_pay';

interface UseGnosisPaySafeMigrationReturn {
  untrackedSafe: Ref<GnosisPayUntrackedSafe | undefined>;
  untrackedAccount: ComputedRef<Account | undefined>;
  hasUntrackedSafe: ComputedRef<boolean>;
  safeMigrationKeypath: ComputedRef<string>;
  adding: Ref<boolean>;
  checkMigration: () => Promise<void>;
  addMissingSafe: () => Promise<void>;
}

/**
 * Consumes the backend `/services/gnosispay/migration` endpoint, which reports the
 * Safe address a user is missing after the Gnosis Pay Safe security migration (when
 * exactly one of the two migration Safes is tracked).
 *
 * @remarks
 * Shared by the Gnosis Pay card and the action center row, so both show the same Safe. It belongs to
 * the logged in user, so it is cleared on logout.
 */
export const useGnosisPaySafeMigration = createSharedComposable((): UseGnosisPaySafeMigrationReturn => {
  const untrackedSafe = ref<GnosisPayUntrackedSafe>();
  const adding = ref<boolean>(false);

  const hasUntrackedSafe = computed<boolean>(() => isDefined(untrackedSafe));

  // i18n keypath for the "missing Safe" message; branded so the key-usage lint counts the keys.
  const safeMigrationKeypath = computed<string>(() => get(untrackedSafe)?.type === 'new'
    ? msg.$t('external_services.gnosispay.safe_migration.missing_new')
    : msg.$t('external_services.gnosispay.safe_migration.missing_old'));

  const untrackedAccount = computed<Account | undefined>(() => {
    const safe = get(untrackedSafe);
    return safe ? { address: safe.address, chain: Blockchain.GNOSIS } : undefined;
  });

  const { t } = useI18n({ useScope: 'global' });
  const { fetchGnosisPaySafeMigration } = useGnosisPaySiweApi();
  const { addAccounts } = useBlockchainAccountManagement();
  const { showErrorMessage, showSuccessMessage } = useNotifications();
  const { getApiKey, keys, load } = useExternalApiKeys();
  const { logged } = storeToRefs(useSessionAuthStore());

  const isGnosisPayConfigured = async (): Promise<boolean> => {
    if (!isDefined(keys)) // external service keys not loaded yet (e.g. right after login)
      await load();

    return Boolean(getApiKey(GNOSIS_PAY_SERVICE));
  };

  /**
   * Looks for a Safe the migration left untracked.
   *
   * @remarks
   * A failed request means nothing to suggest, since not being premium fails it too, so it is only
   * logged at debug level.
   */
  const checkMigration = async (): Promise<void> => {
    const safe = await pipe(
      findUntrackedSafe({ fetchMigration: fetchGnosisPaySafeMigration, isConfigured: isGnosisPayConfigured }),
      match({
        err: (error: unknown): GnosisPayUntrackedSafe | undefined => {
          logger.debug(`Failed to fetch Gnosis Pay Safe migration: ${getErrorMessage(error)}`);
          return undefined;
        },
        ok: found => getOr(found, undefined),
      }),
    );
    set(untrackedSafe, safe);
  };

  const addMissingSafe = async (): Promise<void> => {
    const safe = get(untrackedSafe);
    if (!safe)
      return;

    set(adding, true);
    const title = t('external_services.gnosispay.safe_migration.title');
    await pipe(
      fromAsync(async () => addAccounts(Blockchain.GNOSIS, {
        payload: [{
          address: safe.address,
          label: t('external_services.gnosispay.safe_migration.account_label'),
          tags: null,
        }],
      }, { wait: true }), getErrorMessage),
      flatMap(async summary => readSafeAddition(summary)),
      match({
        err: (error: string): void => {
          showErrorMessage(title, t('external_services.gnosispay.safe_migration.add_error', { error }));
        },
        ok: (added): void => {
          if (!added)
            return;
          set(untrackedSafe, undefined);
          showSuccessMessage(title, t('external_services.gnosispay.safe_migration.add_success', { address: safe.address }));
        },
      }),
    );
    set(adding, false);
  };

  watch(logged, (isLogged) => {
    if (!isLogged)
      set(untrackedSafe, undefined);
  });

  return {
    addMissingSafe,
    adding,
    checkMigration,
    hasUntrackedSafe,
    safeMigrationKeypath,
    untrackedAccount,
    untrackedSafe,
  };
});
