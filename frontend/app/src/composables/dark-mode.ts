import { ThemeMode, useRotkiTheme } from '@rotki/ui-library-compat';
import { getColors } from 'theme-colors';
import type { ThemeColors } from '@rotki/common/lib/settings';

export const useDarkMode = createSharedComposable(() => {
  const { config, switchThemeScheme, setThemeConfig } = useRotkiTheme();
  const store = useSessionStore();
  const { darkModeEnabled } = storeToRefs(store);
  const { darkTheme, lightTheme } = storeToRefs(useFrontendSettingsStore());

  const updateDarkMode = (enabled: boolean) => {
    set(darkModeEnabled, enabled);
  };

  const getColorScheme = (palette: Record<string, string>) => ({
    DEFAULT: hexToRgbPoints(palette['500']).join(', '),
    lighter: hexToRgbPoints(palette['300']).join(', '),
    darker: hexToRgbPoints(palette['600']).join(', '),
  });

  const updateThemeColors = (variant: 'light' | 'dark', theme: ThemeColors) => {
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

  watchDeep(darkTheme, (theme) => {
    updateThemeColors('dark', theme);
  }, {
    immediate: true,
  });

  watchDeep(lightTheme, (theme) => {
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
  };
});
