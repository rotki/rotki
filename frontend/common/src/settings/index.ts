import { z } from "zod";

export type DebugSettings = { vuex: boolean };

export interface Themes {
  readonly light: ThemeColors;
  readonly dark: ThemeColors;
}

export const ThemeColors = z.object({
  primary: z.string(),
  accent: z.string(),
  graph: z.string()
})

export type ThemeColors = z.infer<typeof ThemeColors>;

export enum TimeUnit {
  YEAR = 'year',
  MONTH = 'month',
  WEEK = 'week',
  DAY = 'day'
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