import type { UserSettingsModel } from '@/modules/settings/types/user-settings';
import { assert } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Currency, CURRENCY_USD } from '@/modules/assets/amount-display/currencies';
import { Module } from '@/modules/core/common/modules';
import { defaultAccountingSettings, defaultGeneralSettings } from '@/modules/settings/factories';
import { getDefaultFrontendSettings } from '@/modules/settings/types/frontend-settings';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import '@test/i18n';

const mockSetSettings = vi.fn();
const mockShowErrorMessage = vi.fn();
const mockShowSuccessMessage = vi.fn();
const mockAddQueriedAddress = vi.fn();

vi.mock('@/modules/settings/api/use-settings-api', () => ({
  useSettingsApi: vi.fn(() => ({
    setSettings: mockSetSettings,
  })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  getErrorMessage: vi.fn((e: unknown): string => (e instanceof Error ? e.message : String(e))),
  useNotifications: vi.fn(() => ({
    showErrorMessage: mockShowErrorMessage,
    showSuccessMessage: mockShowSuccessMessage,
  })),
}));

vi.mock('@/modules/accounts/use-queried-address-operations', () => ({
  useQueriedAddressOperations: vi.fn(() => ({
    addQueriedAddress: mockAddQueriedAddress,
  })),
}));

vi.mock('@/modules/session/use-items-per-page', () => ({
  useItemsPerPage: vi.fn(() => ref<number>(10)),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: {
    debug: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

function createSettingsResponse(overrides?: Partial<UserSettingsModel>): UserSettingsModel {
  const mainCurrency = new Currency('US Dollar', CURRENCY_USD, '$');
  return {
    accounting: defaultAccountingSettings(),
    data: { lastBalanceSave: 0, lastDataUploadTs: 0, lastWriteTs: 0, version: 0 },
    general: defaultGeneralSettings(mainCurrency),
    other: {
      frontendSettings: getDefaultFrontendSettings(),
      havePremium: false,
      premiumShouldSync: false,
    },
    ...overrides,
  };
}

describe('useSettingsOperations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  async function importModule(): Promise<typeof import('./use-settings-operations')> {
    return import('./use-settings-operations');
  }

  describe('update', () => {
    it('should update settings successfully', async () => {
      const response = createSettingsResponse();
      mockSetSettings.mockResolvedValue(response);

      const { useSettingsOperations } = await importModule();
      const { update } = useSettingsOperations();
      const result = await update({ uiFloatingPrecision: 2 });

      expect(result.success).toBe(true);
      expect(mockSetSettings).toHaveBeenCalledWith({ uiFloatingPrecision: 2 });
    });

    it('should return error message on failure', async () => {
      mockSetSettings.mockRejectedValue(new Error('settings error'));

      const { useSettingsOperations } = await importModule();
      const { update } = useSettingsOperations();
      const result = await update({ uiFloatingPrecision: 2 });

      expect(result.success).toBe(false);
      assert(!result.success);
      expect(result.message).toBe('settings error');
    });
  });

  describe('setKrakenAccountType', () => {
    it('should update kraken account type and show success', async () => {
      const response = createSettingsResponse();
      mockSetSettings.mockResolvedValue(response);

      const { useSettingsOperations } = await importModule();
      const { setKrakenAccountType } = useSettingsOperations();
      await setKrakenAccountType('starter');

      expect(mockSetSettings).toHaveBeenCalledWith({ krakenAccountType: 'starter' });
      expect(mockShowSuccessMessage).toHaveBeenCalledOnce();
    });

    it('should show error on failure', async () => {
      mockSetSettings.mockRejectedValue(new Error('kraken error'));

      const { useSettingsOperations } = await importModule();
      const { setKrakenAccountType } = useSettingsOperations();
      await setKrakenAccountType('starter');

      expect(mockShowErrorMessage).toHaveBeenCalledOnce();
    });
  });

  describe('enableModule', () => {
    it('should enable module and add queried addresses', async () => {
      const response = createSettingsResponse();
      mockSetSettings.mockResolvedValue(response);
      mockAddQueriedAddress.mockResolvedValue(undefined);

      const { useSettingsOperations } = await importModule();
      const { enableModule } = useSettingsOperations();
      await enableModule({
        enable: [Module.MAKERDAO_DSR],
        addresses: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
      });

      expect(mockSetSettings).toHaveBeenCalledWith({
        activeModules: [Module.MAKERDAO_DSR],
      });
      expect(mockAddQueriedAddress).toHaveBeenCalledWith({
        address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
        module: Module.MAKERDAO_DSR,
      });
    });

    it('should merge with existing active modules without duplicates', async () => {
      const generalStore = useGeneralSettingsStore();
      generalStore.update({
        ...generalStore.settings,
        activeModules: [Module.MAKERDAO_DSR],
      });

      const response = createSettingsResponse();
      mockSetSettings.mockResolvedValue(response);
      mockAddQueriedAddress.mockResolvedValue(undefined);

      const { useSettingsOperations } = await importModule();
      const { enableModule } = useSettingsOperations();
      await enableModule({
        enable: [Module.MAKERDAO_DSR, Module.UNISWAP],
        addresses: ['0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5'],
      });

      const calledModules = mockSetSettings.mock.calls[0][0].activeModules;
      expect(calledModules).toContain(Module.MAKERDAO_DSR);
      expect(calledModules).toContain(Module.UNISWAP);
      // No duplicates
      expect(calledModules.filter((m: Module) => m === Module.MAKERDAO_DSR)).toHaveLength(1);
    });
  });
});
