import type { ThemeColors } from '@rotki/common';

const LIGHT_PRIMARY = '#4e5ba6';

const LIGHT_ACCENT = '#667085';

const LIGHT_GRAPH = '#96DFD2';

const DARK_PRIMARY = '#5b68b2';

const DARK_ACCENT = '#667085';

const DARK_GRAPH = '#E96930';

export const DARK_COLORS: ThemeColors = {
  accent: DARK_ACCENT,
  graph: DARK_GRAPH,
  primary: DARK_PRIMARY,
};

export const LIGHT_COLORS: ThemeColors = {
  accent: LIGHT_ACCENT,
  graph: LIGHT_GRAPH,
  primary: LIGHT_PRIMARY,
};

export const CURRENT_DEFAULT_THEME_VERSION = 2;

interface DefaultThemeHistory {
  version: number;
  lightColors: ThemeColors;
  darkColors: ThemeColors;
}

export const DEFAULT_THEME_HISTORIES: DefaultThemeHistory[] = [
  {
    darkColors: {
      accent: '#ff8a50',
      graph: '#E96930',
      primary: '#ff5722',
    },
    lightColors: {
      accent: '#e45325',
      graph: '#96DFD2',
      primary: '#7e4a3b',
    },
    version: 1,
  },
];
