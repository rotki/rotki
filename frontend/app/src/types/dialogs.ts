import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';

export const DialogType = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
} as const;

export type DialogType = (typeof DialogType)[keyof typeof DialogType];

export interface DialogTheme {
  readonly icon: RuiIcons;
  readonly color: ContextColorsType;
}

export type DialogThemes = { [type in DialogType]: DialogTheme };

export const themes: DialogThemes = {
  info: { color: 'primary', icon: 'information-line' },
  success: { color: 'success', icon: 'checkbox-circle-line' },
  warning: { color: 'error', icon: 'error-warning-line' },
} as const;
