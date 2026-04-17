import type { KrakenAccountType } from '@/modules/balances/types/exchanges';
import type { ActionStatus } from '@/modules/core/common/action';
import type { Module } from '@/modules/core/common/modules';
import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import type { SettingsUpdate } from '@/modules/settings/types/user-settings';
import { assert, BigNumber } from '@rotki/common';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { getBnFormat } from '@/modules/assets/amount-display/amount-formatter';
import { snakeCaseTransformer } from '@/modules/core/api/transformers';
import { ApiValidationError } from '@/modules/core/api/types/errors';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { usePremiumStore } from '@/modules/premium/use-premium-store';
import { useItemsPerPage } from '@/modules/session/use-items-per-page';
import { useSettingsApi } from '@/modules/settings/api/use-settings-api';
import { useAccountingSettingsStore } from '@/modules/settings/use-accounting-settings-store';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function extractSettingsFieldError(errors: Record<string, string | string[]>, key: string): string | undefined {
  const settingsValue: unknown = errors.settings;
  if (!isRecord(settingsValue) || !(key in settingsValue))
    return undefined;

  const value = settingsValue[key];
  if (typeof value === 'string')
    return value;
  if (Array.isArray(value))
    return value.join(', ');
  return undefined;
}

interface UseSettingsOperationsReturn {
  applyFrontendSettingLocal: (payload: FrontendSettingsPayload) => void;
  enableModule: (payload: { readonly enable: Module[]; readonly addresses: string[] }) => Promise<void>;
  setKrakenAccountType: (krakenAccountType: KrakenAccountType) => Promise<void>;
  update: (update: SettingsUpdate) => Promise<ActionStatus>;
  updateFrontendSetting: (payload: FrontendSettingsPayload) => Promise<ActionStatus>;
}

export function useSettingsOperations(): UseSettingsOperationsReturn {
  const { showErrorMessage, showSuccessMessage } = useNotifications();
  const { addQueriedAddress } = useQueriedAddressOperations();
  const generalStore = useGeneralSettingsStore();
  const accountingStore = useAccountingSettingsStore();
  const frontendStore = useFrontendSettingsStore();
  const { premium, premiumSync } = storeToRefs(usePremiumStore());
  const { t } = useI18n({ useScope: 'global' });

  const api = useSettingsApi();
  const globalItemsPerPage = useItemsPerPage();

  function handleErrors(error: unknown, keys: string[]): string {
    if (!(error instanceof ApiValidationError)) {
      return getErrorMessage(error);
    }

    // The backend may return nested settings errors where `errors.settings` is a record of field→message(s).
    // The ValidationErrors type doesn't capture this nesting, so we extract with a type guard.
    if (keys.length === 1) {
      const fieldError = extractSettingsFieldError(error.errors, keys[0]);
      if (fieldError)
        return fieldError;
    }

    return getErrorMessage(error);
  }

  const setKrakenAccountType = async (krakenAccountType: KrakenAccountType): Promise<void> => {
    try {
      const { general } = await api.setSettings({
        krakenAccountType,
      });
      generalStore.update(general);
      showSuccessMessage(t('actions.session.kraken_account.success.title'), t('actions.session.kraken_account.success.message'));
    }
    catch (error: unknown) {
      showErrorMessage(t('actions.session.kraken_account.error.title'), getErrorMessage(error));
    }
  };

  const update = async (payload: SettingsUpdate): Promise<ActionStatus> => {
    let success = false;
    let message = '';
    try {
      const {
        accounting,
        general,
        other: { havePremium, premiumShouldSync },
      } = await api.setSettings(payload);
      set(premium, havePremium);
      set(premiumSync, premiumShouldSync);
      generalStore.update(general);
      accountingStore.update(accounting);
      success = true;
    }
    catch (error: unknown) {
      logger.error(error);
      message = handleErrors(error, Object.keys(payload));
    }
    return {
      message,
      success,
    };
  };

  const enableModule = async (payload: { readonly enable: Module[]; readonly addresses: string[] }): Promise<void> => {
    const activeModules = generalStore.activeModules;
    const modules: Module[] = [...activeModules, ...payload.enable].filter(uniqueStrings);

    await update({ activeModules: modules });

    for (const module of payload.enable) {
      for (const address of payload.addresses) await addQueriedAddress({ address, module });
    }
  };

  function applyFrontendSettingLocal(payload: FrontendSettingsPayload): void {
    const currentSettings = get(frontendStore.settings);
    frontendStore.update({ ...currentSettings, ...payload });
  }

  async function updateFrontendSetting(payload: FrontendSettingsPayload): Promise<ActionStatus> {
    const props = Object.keys(payload);
    assert(props.length > 0, 'Payload must be not-empty');
    try {
      const currentSettings = get(frontendStore.settings);
      const updatedSettings = { ...currentSettings, ...payload };
      const { other } = await api.setSettings({
        frontendSettings: JSON.stringify(snakeCaseTransformer(updatedSettings)),
      });

      frontendStore.update(updatedSettings);

      if (payload.thousandSeparator || payload.decimalSeparator) {
        BigNumber.config({
          FORMAT: getBnFormat(other.frontendSettings.thousandSeparator, other.frontendSettings.decimalSeparator),
        });
      }

      return {
        success: true,
      };
    }
    catch (error: unknown) {
      logger.error(error);
      return {
        message: getErrorMessage(error),
        success: false,
      };
    }
  }

  watchDebounced(globalItemsPerPage, async (value, oldValue): Promise<void> => {
    if (oldValue === undefined || value === oldValue)
      return;

    try {
      await updateFrontendSetting({ itemsPerPage: value });
    }
    catch (error: unknown) {
      logger.error(error);
    }
  }, { debounce: 800, maxWait: 1200 });

  return {
    applyFrontendSettingLocal,
    enableModule,
    setKrakenAccountType,
    update,
    updateFrontendSetting,
  };
}
