import type { ThemeColors } from '@rotki/common';
import { ThemeMode } from '@rotki/ui-library';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useDarkMode } from '@/modules/shell/theme/use-dark-mode';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';

const PREMIUM_DARK: ThemeColors = { accent: '#111111', graph: '#191919', primary: '#222222' };
const PREMIUM_LIGHT: ThemeColors = { accent: '#333333', graph: '#3a3a3a', primary: '#444444' };

const mockConfig = ref<Record<string, unknown> | undefined>({ dark: {}, light: {} });
const mockIsDark = ref<boolean>(false);
const mockSetThemeConfig = vi.fn();
const mockSwitchThemeScheme = vi.fn();
const mockDarkTheme = ref<ThemeColors>(PREMIUM_DARK);
const mockLightTheme = ref<ThemeColors>(PREMIUM_LIGHT);
const mockPremium = ref<boolean>(false);

vi.mock('@rotki/ui-library', async importOriginal => ({
  ...await importOriginal<typeof import('@rotki/ui-library')>(),
  useRotkiTheme: (): Record<string, unknown> => ({
    config: mockConfig,
    isDark: mockIsDark,
    setThemeConfig: mockSetThemeConfig,
    switchThemeScheme: mockSwitchThemeScheme,
  }),
}));

vi.mock('@/modules/shell/theme/use-theme-settings', () => ({
  useThemeSettings: (): { darkTheme: typeof mockDarkTheme; lightTheme: typeof mockLightTheme } => ({
    darkTheme: mockDarkTheme,
    lightTheme: mockLightTheme,
  }),
}));

vi.mock('@/modules/premium/use-premium', () => ({
  usePremium: (): typeof mockPremium => mockPremium,
}));

describe('useDarkMode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockConfig, { dark: {}, light: {} });
    set(mockIsDark, false);
    set(mockDarkTheme, PREMIUM_DARK);
    set(mockLightTheme, PREMIUM_LIGHT);
    set(mockPremium, false);
    useDarkMode(); // instantiate the shared composable
  });

  it('should switch to dark mode when enabled', () => {
    useDarkMode().updateDarkMode(true);
    expect(mockSwitchThemeScheme).toHaveBeenCalledWith(ThemeMode.dark);
  });

  it('should switch to light mode when disabled', () => {
    useDarkMode().updateDarkMode(false);
    expect(mockSwitchThemeScheme).toHaveBeenCalledWith(ThemeMode.light);
  });

  it('should use the default colors when not premium', () => {
    const { usedTheme } = useDarkMode();
    set(mockIsDark, false);
    expect(get(usedTheme)).toStrictEqual(LIGHT_COLORS);
    set(mockIsDark, true);
    expect(get(usedTheme)).toStrictEqual(DARK_COLORS);
  });

  it('should use the configured premium themes when premium', () => {
    set(mockPremium, true);
    const { usedTheme } = useDarkMode();
    set(mockIsDark, false);
    expect(get(usedTheme)).toStrictEqual(PREMIUM_LIGHT);
    set(mockIsDark, true);
    expect(get(usedTheme)).toStrictEqual(PREMIUM_DARK);
  });

  it('should recompute theme colors when the premium dark theme changes', async () => {
    set(mockPremium, true);
    useDarkMode();
    await nextTick();
    mockSetThemeConfig.mockClear();

    set(mockDarkTheme, { accent: '#555555', graph: '#5a5a5a', primary: '#666666' });
    await nextTick();

    expect(mockSetThemeConfig).toHaveBeenCalled();
    const config = mockSetThemeConfig.mock.calls.at(-1)?.[0];
    expect(config?.dark?.primary).toBeDefined();
    expect(config?.dark?.secondary).toBeDefined();
  });

  it('should not push theme config when the base config is missing', async () => {
    set(mockPremium, true);
    useDarkMode();
    await nextTick();
    set(mockConfig, undefined);
    mockSetThemeConfig.mockClear();

    set(mockDarkTheme, { accent: '#777777', graph: '#7a7a7a', primary: '#888888' });
    await nextTick();

    expect(mockSetThemeConfig).not.toHaveBeenCalled();
  });
});
