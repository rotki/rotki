import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useThemeMigration } from './use-theme-migration';

const darkTheme = ref<Record<string, string>>({});
const lightTheme = ref<Record<string, string>>({});
const defaultThemeVersion = ref<number>(0);
const updateFrontendSetting = vi.fn().mockResolvedValue(undefined);

vi.mock('@/modules/settings/use-frontend-settings-store', () => ({
  useFrontendSettingsStore: (): object => ({ darkTheme, defaultThemeVersion, lightTheme }),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

vi.mock('@/plugins/theme', () => ({
  CURRENT_DEFAULT_THEME_VERSION: 2,
  DARK_COLORS: {},
  LIGHT_COLORS: {},
  DEFAULT_THEME_HISTORIES: [{ version: 0, darkColors: {}, lightColors: {} }],
}));

describe('useThemeMigration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(darkTheme, {});
    set(lightTheme, {});
    set(defaultThemeVersion, 0);
  });

  it('should do nothing when the theme version is already current', () => {
    set(defaultThemeVersion, 2);
    useThemeMigration().checkDefaultThemeVersion();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should do nothing when there is no matching historic default', () => {
    set(defaultThemeVersion, 1);
    useThemeMigration().checkDefaultThemeVersion();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should migrate to the current version when an outdated default is found', () => {
    set(defaultThemeVersion, 0);
    useThemeMigration().checkDefaultThemeVersion();
    expect(updateFrontendSetting).toHaveBeenCalledOnce();
    expect(updateFrontendSetting).toHaveBeenCalledWith(
      expect.objectContaining({ defaultThemeVersion: 2 }),
    );
  });
});
