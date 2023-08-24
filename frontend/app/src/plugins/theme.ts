import { type ThemeColors } from '@rotki/common/lib/settings';

export const LIGHT_PRIMARY = '#4e5ba6';

export const LIGHT_ACCENT = '#667085';

export const LIGHT_ERROR = '#d32f2f';

export const LIGHT_INFO = '#0289d1';

export const LIGHT_SUCCESS = '#2e7d32';

export const LIGHT_WARNING = '#ed6c02';

export const LIGHT_GRAPH = '#96DFD2';

export const DARK_PRIMARY = '#5b68b2';

export const DARK_ACCENT = '#667085';

export const DARK_ERROR = '#f44336';

export const DARK_INFO = '#29b5f6';

export const DARK_SUCCESS = '#66bb6a';

export const DARK_WARNING = '#ffa826';

export const DARK_GRAPH = '#E96930';

export const DARK_COLORS: ThemeColors = {
  primary: DARK_PRIMARY,
  accent: DARK_ACCENT,
  graph: DARK_GRAPH
};

export const LIGHT_COLORS: ThemeColors = {
  primary: LIGHT_PRIMARY,
  accent: LIGHT_ACCENT,
  graph: LIGHT_GRAPH
};

export const CURRENT_DEFAULT_THEME_VERSION = 2;

interface DefaultThemeHistory {
  version: number;
  lightColors: ThemeColors;
  darkColors: ThemeColors;
}

export const DEFAULT_THEME_HISTORIES: DefaultThemeHistory[] = [
  {
    version: 1,
    lightColors: {
      primary: '#7e4a3b',
      accent: '#e45325',
      graph: '#96DFD2'
    },
    darkColors: {
      primary: '#ff5722',
      accent: '#ff8a50',
      graph: '#E96930'
    }
  }
];
