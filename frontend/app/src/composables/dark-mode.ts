import { ThemeMode, useRotkiTheme } from '@rotki/ui-library';
import { getColors } from 'theme-colors';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import type { ThemeColors } from '@rotki/common';

interface ColorScheme { DEFAULT: string; lighter: string; darker: string }

export const useDarkMode = createSharedComposable(() => {
  const { config, switchThemeScheme, setThemeConfig } = useRotkiTheme();
  const store = useSessionStore();
  const { darkModeEnabled } = storeToRefs(store);
  const { darkTheme, lightTheme } = storeToRefs(useFrontendSettingsStore());

  const premium = usePremium();

  const updateDarkMode = (enabled: boolean): void => {
    set(darkModeEnabled, enabled);
  };

  const getColorScheme = (palette: Record<string, string>): ColorScheme => ({
    DEFAULT: hexToRgbPoints(palette['500']).join(', '),
    lighter: hexToRgbPoints(palette['300']).join(', '),
    darker: hexToRgbPoints(palette['600']).join(', '),
  });

  const updateThemeColors = (variant: 'light' | 'dark', theme: ThemeColors): void => {
    const conf = get(config);
    if (!conf)
      return;

    const primaryColors = getColors(theme.primary);
    const secondaryColors = getColors(theme.accent);

    const newColors = {
      primary: getColorScheme(primaryColors),
      secondary: getColorScheme(secondaryColors),
    };

    const variantConf = { ...conf[variant], ...newColors };

    setThemeConfig({ ...conf, [variant]: variantConf });
  };

  // Use default theme if not premium
  const usedDarkTheme = computed(() => (get(premium) ? get(darkTheme) : DARK_COLORS));
  const usedLightTheme = computed(() => (get(premium) ? get(lightTheme) : LIGHT_COLORS));

  const usedTheme = computed(() => (get(darkModeEnabled) ? get(usedDarkTheme) : get(usedLightTheme)));

  watchDeep(usedDarkTheme, (theme) => {
    updateThemeColors('dark', theme);
  }, {
    immediate: true,
  });

  watchDeep(usedLightTheme, (theme) => {
    updateThemeColors('light', theme);
  }, {
    immediate: true,
  });

  watchImmediate(darkModeEnabled, (enabled) => {
    switchThemeScheme(enabled ? ThemeMode.dark : ThemeMode.light);
  });

  return {
    darkModeEnabled,
    updateDarkMode,
    usedTheme,
  };
});
