import { ThemeColors } from '@rotki/common';
import { CURRENT_DEFAULT_THEME_VERSION, DARK_COLORS, DEFAULT_THEME_HISTORIES, LIGHT_COLORS } from '@/plugins/theme';

interface UseThemeMigrationReturn { checkDefaultThemeVersion: () => void }

export function useThemeMigration(): UseThemeMigrationReturn {
  const store = useFrontendSettingsStore();
  const { defaultThemeVersion, lightTheme, darkTheme } = storeToRefs(store);
  const { updateSetting } = store;

  function checkDefaultThemeVersion(): void {
    const defaultThemeVersionSetting = get(defaultThemeVersion);
    if (defaultThemeVersionSetting >= CURRENT_DEFAULT_THEME_VERSION)
      return;

    const historicDefaultTheme = DEFAULT_THEME_HISTORIES.find(({ version }) => version === defaultThemeVersionSetting);

    if (!historicDefaultTheme)
      return;

    const newLightTheme: ThemeColors = { ...LIGHT_COLORS };
    const newDarkTheme: ThemeColors = { ...DARK_COLORS };
    const savedLightTheme = get(lightTheme);
    const savedDarkTheme = get(darkTheme);
    const accentColors = Object.keys(ThemeColors.shape);

    const isKeyOfThemeColors = (key: string): key is keyof ThemeColors => accentColors.includes(key);

    accentColors.forEach((key) => {
      if (!isKeyOfThemeColors(key))
        return;

      // If saved theme isn't the same with the default theme at that version, do not replace with new default.
      if (historicDefaultTheme.lightColors[key] !== savedLightTheme[key])
        newLightTheme[key] = savedLightTheme[key];

      if (historicDefaultTheme.darkColors[key] !== savedDarkTheme[key])
        newDarkTheme[key] = savedDarkTheme[key];
    });

    startPromise(
      updateSetting({
        lightTheme: newLightTheme,
        darkTheme: newDarkTheme,
        defaultThemeVersion: CURRENT_DEFAULT_THEME_VERSION,
      }),
    );
  }

  return { checkDefaultThemeVersion };
}
