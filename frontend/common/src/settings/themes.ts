import z from 'zod';

export interface Themes {
  readonly light: ThemeColors;
  readonly dark: ThemeColors;
}

export const ThemeColors = z.object({
  primary: z.string(),
  accent: z.string(),
  graph: z.string(),
});

export type ThemeColors = z.infer<typeof ThemeColors>;

export enum Theme {
  DARK = 0,
  AUTO = 1,
  LIGHT = 2,
}

export const ThemeEnum = z.nativeEnum(Theme);

export const SELECTED_THEME = 'selectedTheme';

export const LIGHT_THEME = 'lightTheme';

export const DARK_THEME = 'darkTheme';
