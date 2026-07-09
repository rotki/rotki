import type { Ref } from 'vue';
import { type SettingValue, useSetting } from '@/modules/settings/use-setting';

export interface ThemeSettings {
  lightTheme: Readonly<Ref<SettingValue<'lightTheme'>>>;
  darkTheme: Readonly<Ref<SettingValue<'darkTheme'>>>;
  defaultThemeVersion: Readonly<Ref<SettingValue<'defaultThemeVersion'>>>;
}

/**
 * Domain facade bundling the theme customization settings consumed together by the theme
 * renderer, the default-theme migration, and the premium interface setup. Each entry reads
 * through `useSetting`, so this composable knows nothing about which store owns each key.
 * Theme *mode* (`selectedTheme`) is a separate single-key read and is intentionally not bundled here.
 */
export function useThemeSettings(): ThemeSettings {
  return {
    darkTheme: useSetting('darkTheme'),
    defaultThemeVersion: useSetting('defaultThemeVersion'),
    lightTheme: useSetting('lightTheme'),
  };
}
