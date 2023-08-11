import { ThemeMode, useRotkiTheme } from '@rotki/ui-library-compat';

export const useDarkMode = createSharedComposable(() => {
  const { config, switchThemeScheme, setThemeConfig } = useRotkiTheme();
  const { theme } = useTheme();
  const store = useSessionStore();
  const { darkModeEnabled } = storeToRefs(store);

  const updateDarkMode = (enabled: boolean) => {
    set(darkModeEnabled, enabled);
  };

  watchDeep(
    theme,
    theme => {
      // @ts-ignore
      const themes = theme.parsedTheme!;
      const defaultConfig = get(config)!;
      const newColors = {
        primary: {
          DEFAULT: hexToRgbPoints(themes.primary.base).join(', '),
          lighter: hexToRgbPoints(themes.primary.lighten4).join(', '),
          darker: hexToRgbPoints(themes.primary.darken1).join(', ')
        },
        secondary: {
          DEFAULT: hexToRgbPoints(themes.accent.base).join(', '),
          lighter: hexToRgbPoints(themes.accent.lighten4).join(', '),
          darker: hexToRgbPoints(themes.accent.darken1).join(', ')
        }
      };

      const newConfig = {
        dark: {
          ...defaultConfig.dark,
          ...newColors
        },
        light: {
          ...defaultConfig.light,
          ...newColors
        }
      };

      setThemeConfig(newConfig);
    },
    { immediate: true }
  );

  watchImmediate(darkModeEnabled, enabled => {
    switchThemeScheme(enabled ? ThemeMode.dark : ThemeMode.light);
  });

  return {
    darkModeEnabled,
    updateDarkMode
  };
});
