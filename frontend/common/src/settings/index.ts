import { z } from 'zod';

export interface DebugSettings {
  persistStore: boolean;
}

export interface Themes {
  readonly light: ThemeColors;
  readonly dark: ThemeColors;
}

export const ThemeColors = z.object({
  primary: z.string(),
  accent: z.string(),
  graph: z.string()
});

export type ThemeColors = z.infer<typeof ThemeColors>;

export enum Theme {
  DARK = 0,
  AUTO = 1,
  LIGHT = 2
}

export const ThemeEnum = z.nativeEnum(Theme);

export enum TimeUnit {
  YEAR = 'year',
  MONTH = 'month',
  WEEK = 'week',
  DAY = 'day'
}

export const SELECTED_THEME = 'selectedTheme' as const;
export const LIGHT_THEME = 'lightTheme' as const;
export const DARK_THEME = 'darkTheme' as const;

interface FrontendSettings {
  readonly [SELECTED_THEME]: Theme;
  readonly [LIGHT_THEME]: ThemeColors;
  readonly [DARK_THEME]: ThemeColors;
}

export type FrontendSettingsPayload = Partial<FrontendSettings>;
