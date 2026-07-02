import type { ComputedRef, Ref } from 'vue';
import type { GnosisPaySafeMigration, GnosisPayUntrackedSafe } from '@/modules/integrations/gnosis-pay/types';
import { type Account, Blockchain, NotificationCategory, Priority, Severity } from '@rotki/common';
import dayjs from 'dayjs';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useGnosisPaySiweApi } from '@/modules/integrations/gnosis-pay/use-gnosis-pay-api';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

const WEEK_IN_SECONDS = 7 * 24 * 60 * 60;
const GNOSIS_PAY_SERVICE = 'gnosis_pay';

interface UseGnosisPaySafeMigrationReturn {
  untrackedSafe: Ref<GnosisPayUntrackedSafe | undefined>;
  untrackedAccount: ComputedRef<Account | undefined>;
  hasUntrackedSafe: ComputedRef<boolean>;
  adding: Ref<boolean>;
  checkMigration: () => Promise<void>;
  addMissingSafe: () => Promise<void>;
  checkAndNotify: () => Promise<void>;
}

/**
 * Consumes the backend `/services/gnosispay/migration` endpoint, which reports the
 * Safe address a user is missing after the Gnosis Pay Safe security migration (when
 * exactly one of the two migration Safes is tracked). The request is skipped unless
 * Gnosis Pay is configured, and it is premium-gated, so a failed fetch is swallowed.
 */
export const useGnosisPaySafeMigration = createSharedComposable((): UseGnosisPaySafeMigrationReturn => {
  const untrackedSafe = ref<GnosisPayUntrackedSafe>();
  const adding = ref<boolean>(false);

  const hasUntrackedSafe = computed<boolean>(() => isDefined(untrackedSafe));

  const untrackedAccount = computed<Account | undefined>(() => {
    const safe = get(untrackedSafe);
    return safe ? { address: safe.address, chain: Blockchain.GNOSIS } : undefined;
  });

  const { t } = useI18n({ useScope: 'global' });
  const { fetchGnosisPaySafeMigration } = useGnosisPaySiweApi();
  const { addAccounts } = useBlockchainAccountManagement();
  const { notify, showErrorMessage, showSuccessMessage } = useNotifications();
  const { updateFrontendSetting } = useSettingsOperations();
  const settingsStore = useFrontendSettingsStore();
  const { getApiKey, keys, load } = useExternalApiKeys();

  const isGnosisPayConfigured = async (): Promise<boolean> => {
    if (!isDefined(keys)) // external service keys not loaded yet (e.g. right after login)
      await load();

    return Boolean(getApiKey(GNOSIS_PAY_SERVICE));
  };

  const checkMigration = async (): Promise<void> => {
    // Skip the (premium-gated) request entirely when Gnosis Pay is not configured.
    if (!await isGnosisPayConfigured()) {
      set(untrackedSafe, undefined);
      return;
    }

    try {
      const migration: GnosisPaySafeMigration = await fetchGnosisPaySafeMigration();
      set(untrackedSafe, migration.untrackedAddresses[0]);
    }
    catch (error: unknown) {
      // Not premium / remote error: nothing to suggest.
      logger.debug(`Failed to fetch Gnosis Pay Safe migration: ${getErrorMessage(error)}`);
      set(untrackedSafe, undefined);
    }
  };

  const addMissingSafe = async (): Promise<void> => {
    const safe = get(untrackedSafe);
    if (!safe)
      return;

    set(adding, true);
    try {
      await addAccounts(Blockchain.GNOSIS, {
        payload: [{
          address: safe.address,
          label: t('external_services.gnosispay.safe_migration.account_label'),
          tags: null,
        }],
      }, { wait: true });
      set(untrackedSafe, undefined);
      showSuccessMessage(
        t('external_services.gnosispay.safe_migration.title'),
        t('external_services.gnosispay.safe_migration.add_success', { address: safe.address }),
      );
    }
    catch (error: unknown) {
      showErrorMessage(
        t('external_services.gnosispay.safe_migration.title'),
        t('external_services.gnosispay.safe_migration.add_error', { error: getErrorMessage(error) }),
      );
    }
    finally {
      set(adding, false);
    }
  };

  const notifyIfNeeded = async (): Promise<void> => {
    const safe = get(untrackedSafe);
    if (!safe || settingsStore.gnosisPaySafeMigrationNeverNotify)
      return;

    const lastNotified = settingsStore.gnosisPaySafeMigrationLastNotified;
    const now = dayjs().unix();
    if (lastNotified !== 0 && (now - lastNotified) <= WEEK_IN_SECONDS)
      return;

    notify({
      action: [
        {
          action: async (): Promise<void> => addMissingSafe(),
          label: t('external_services.gnosispay.safe_migration.add_action'),
        },
        {
          action: async (): Promise<void> => {
            await updateFrontendSetting({ gnosisPaySafeMigrationNeverNotify: true });
          },
          label: t('external_services.gnosispay.safe_migration.never_action'),
        },
      ],
      category: NotificationCategory.DEFAULT,
      display: true,
      message: safe.type === 'new'
        ? t('notification_messages.gnosis_pay_safe_migration.message_new', { address: safe.address })
        : t('notification_messages.gnosis_pay_safe_migration.message_old', { address: safe.address }),
      priority: Priority.ACTION,
      severity: Severity.WARNING,
      title: t('notification_messages.gnosis_pay_safe_migration.title'),
    });

    await updateFrontendSetting({ gnosisPaySafeMigrationLastNotified: now });
  };

  const checkAndNotify = async (): Promise<void> => {
    await checkMigration();
    await notifyIfNeeded();
  };

  return {
    addMissingSafe,
    adding,
    checkAndNotify,
    checkMigration,
    hasUntrackedSafe,
    untrackedAccount,
    untrackedSafe,
  };
});
