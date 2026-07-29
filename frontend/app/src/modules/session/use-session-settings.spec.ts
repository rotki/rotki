import type { Exchange } from '@/modules/balances/types/exchanges';
import type { FrontendSettings } from '@/modules/settings/types/frontend-settings';
import type { UserSettingsModel } from '@/modules/settings/types/user-settings';
import { TimeFramePeriod, TimeFramePersist } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import flushPromises from 'flush-promises';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { useSessionSettings } from '@/modules/session/use-session-settings';

const mockPremium = ref<boolean>(false);
const mockPremiumSync = ref<boolean>(false);
const mockFetchCapabilities = vi.fn();
const mockUpdateAccounting = vi.fn();
const mockUpdateFrontend = vi.fn();
const mockUpdateGeneral = vi.fn();
const mockUpdateSession = vi.fn();
const mockUpdateFrontendSetting = vi.fn();
const mockSetConnectedExchanges = vi.fn();
const mockCheckDefaultThemeVersion = vi.fn();
const mockCheckForSuggestions = vi.fn();

vi.mock('@/modules/premium/use-premium-store', () => ({
  usePremiumStore: vi.fn(() => ({
    premium: mockPremium,
    premiumSync: mockPremiumSync,
  })),
}));

vi.mock('@/modules/premium/use-premium-watchers', () => ({
  usePremiumWatchers: vi.fn(() => ({
    fetchCapabilities: mockFetchCapabilities,
  })),
}));

vi.mock('@/modules/settings/settings-repo', () => ({
  useSettingsRepo: vi.fn(() => ({
    updateAccounting: mockUpdateAccounting,
    updateFrontend: mockUpdateFrontend,
    updateGeneral: mockUpdateGeneral,
    updateSession: mockUpdateSession,
  })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn(() => ({
    updateFrontendSetting: mockUpdateFrontendSetting,
  })),
}));

vi.mock('@/modules/balances/exchanges/use-connected-exchanges-store', () => ({
  useConnectedExchangesStore: vi.fn(() => ({
    setConnectedExchanges: mockSetConnectedExchanges,
  })),
}));

vi.mock('@/modules/settings/use-theme-migration', () => ({
  useThemeMigration: vi.fn(() => ({
    checkDefaultThemeVersion: mockCheckDefaultThemeVersion,
  })),
}));

vi.mock('@/modules/settings/suggestions/use-settings-suggestions', () => ({
  useSettingsSuggestions: vi.fn(() => ({
    checkForSuggestions: mockCheckForSuggestions,
  })),
}));

function frontend(overrides: Partial<FrontendSettings> = {}): FrontendSettings {
  return createMock<FrontendSettings>({
    lastKnownTimeframe: TimeFramePeriod.MONTH,
    persistPrivacySettings: true,
    timeframeSetting: TimeFramePeriod.WEEK,
    ...overrides,
  });
}

interface BuildOverrides {
  frontendSettings?: FrontendSettings;
  havePremium?: boolean;
  premiumShouldSync?: boolean;
}

function buildModel(overrides: BuildOverrides = {}): UserSettingsModel {
  const frontendSettings = 'frontendSettings' in overrides ? overrides.frontendSettings : frontend();
  const havePremium = overrides.havePremium ?? false;
  const premiumShouldSync = overrides.premiumShouldSync ?? false;
  return createMock<UserSettingsModel>({
    accounting: createMock(),
    general: createMock(),
    other: { frontendSettings, havePremium, premiumShouldSync },
  });
}

describe('useSessionSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockPremium, false);
    set(mockPremiumSync, false);
    mockUpdateFrontendSetting.mockResolvedValue(undefined);
    mockFetchCapabilities.mockResolvedValue(undefined);
  });

  it('should apply frontend settings and dependent effects', async () => {
    const { initialize } = useSessionSettings();
    const exchanges: Exchange[] = [];
    await initialize(buildModel(), exchanges);

    expect(mockUpdateFrontend).toHaveBeenCalledOnce();
    expect(mockSetConnectedExchanges).toHaveBeenCalledWith(exchanges);
    expect(mockCheckDefaultThemeVersion).toHaveBeenCalledOnce();
    expect(mockCheckForSuggestions).toHaveBeenCalledWith(expect.anything(), expect.anything(), false);
  });

  it('should flag a new account when checking for suggestions', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel(), [], true);

    expect(mockCheckForSuggestions).toHaveBeenCalledWith(expect.anything(), expect.anything(), true);
  });

  it('should await the suggestions check before resetting privacy settings', async () => {
    let release: () => void = () => {};
    mockCheckForSuggestions.mockReturnValue(new Promise<void>((resolve) => {
      release = resolve;
    }));

    const { initialize } = useSessionSettings();
    const pending = initialize(buildModel({ frontendSettings: frontend({ persistPrivacySettings: false }) }), [], true);
    await flushPromises();

    // both writes rewrite the whole settings blob, so the privacy reset must not overlap
    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();

    release();
    await pending;

    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      privacyMode: PrivacyMode.NORMAL,
      scrambleData: false,
    });
  });

  it('should use the explicit timeframe when it is not REMEMBER', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel({ frontendSettings: frontend({ timeframeSetting: TimeFramePeriod.WEEK }) }), []);

    expect(mockUpdateSession).toHaveBeenCalledWith({ timeframe: TimeFramePeriod.WEEK });
  });

  it('should fall back to the last known timeframe when set to REMEMBER', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel({
      frontendSettings: frontend({ lastKnownTimeframe: TimeFramePeriod.MONTH, timeframeSetting: TimeFramePersist.REMEMBER }),
    }), []);

    expect(mockUpdateSession).toHaveBeenCalledWith({ timeframe: TimeFramePeriod.MONTH });
  });

  it('should reset privacy settings when they should not persist', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel({ frontendSettings: frontend({ persistPrivacySettings: false }) }), []);

    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      privacyMode: PrivacyMode.NORMAL,
      scrambleData: false,
    });
  });

  it('should keep privacy settings when they should persist', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel({ frontendSettings: frontend({ persistPrivacySettings: true }) }), []);

    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should skip the frontend block when there are no frontend settings', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel({ frontendSettings: undefined }), []);

    expect(mockUpdateFrontend).not.toHaveBeenCalled();
    expect(mockCheckForSuggestions).not.toHaveBeenCalled();
    expect(mockSetConnectedExchanges).not.toHaveBeenCalled();
  });

  it('should always apply premium, general and accounting settings', async () => {
    const { initialize } = useSessionSettings();
    await initialize(buildModel({ havePremium: true, premiumShouldSync: true }), []);

    expect(get(mockPremium)).toBe(true);
    expect(get(mockPremiumSync)).toBe(true);
    expect(mockUpdateGeneral).toHaveBeenCalledOnce();
    expect(mockUpdateAccounting).toHaveBeenCalledOnce();
    expect(mockFetchCapabilities).toHaveBeenCalledOnce();
  });
});
