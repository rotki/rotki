export type DebugSettings = { vuex: boolean };

export interface Themes {
  readonly light: ThemeColors;
  readonly dark: ThemeColors;
}

export type ThemeColors = {
  readonly primary: string;
  readonly accent: string;
  readonly graph: string;
};

export enum TimeUnit {
  YEAR = 'year',
  MONTH = 'month',
  WEEK = 'week',
  DAY = 'day',
  HOUR = 'hour'
}

export const DARK_MODE_ENABLED = 'darkModeEnabled' as const;
export const LIGHT_THEME = 'lightTheme' as const;
export const DARK_THEME = 'darkTheme' as const;

type FrontendSettings = {
  readonly [DARK_MODE_ENABLED]: boolean;
  readonly [LIGHT_THEME]: ThemeColors;
  readonly [DARK_THEME]: ThemeColors;
}

export type FrontendSettingsPayload = Partial<FrontendSettings>;
