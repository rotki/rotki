import type { DARK_THEME, LIGHT_THEME, SELECTED_THEME, Theme, ThemeColors } from './themes';

export interface DebugSettings {
  persistStore: boolean;
}

export enum TimeUnit {
  YEAR = 'year',
  MONTH = 'month',
  WEEK = 'week',
  DAY = 'day',
}

interface FrontendSettings {
  readonly [SELECTED_THEME]: Theme;
  readonly [LIGHT_THEME]: ThemeColors;
  readonly [DARK_THEME]: ThemeColors;
}

export type FrontendSettingsPayload = Partial<FrontendSettings>;
