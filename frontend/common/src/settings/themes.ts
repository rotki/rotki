import z from 'zod/v4';

export interface Themes {
  readonly light: ThemeColors;
  readonly dark: ThemeColors;
}

export const ThemeColors = z.object({
  accent: z.string(),
  graph: z.string(),
  primary: z.string(),
});

export type ThemeColors = z.infer<typeof ThemeColors>;

export enum Theme {
  DARK = 0,
  AUTO = 1,
  LIGHT = 2,
}

export const ThemeEnum = z.enum(Theme);

export const SELECTED_THEME = 'selectedTheme';

export const LIGHT_THEME = 'lightTheme';

export const DARK_THEME = 'darkTheme';
