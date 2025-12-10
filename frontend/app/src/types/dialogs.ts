import type { ContextColorsType, RuiIcons } from '@rotki/ui-library';

export const DialogType = {
  INFO: 'info',
  SUCCESS: 'success',
  WARNING: 'warning',
} as const;

export type DialogType = (typeof DialogType)[keyof typeof DialogType];

interface DialogTheme {
  readonly icon: RuiIcons;
  readonly color: ContextColorsType;
}

type DialogThemes = { [type in DialogType]: DialogTheme };

export const themes: DialogThemes = {
  info: { color: 'primary', icon: 'lu-info' },
  success: { color: 'success', icon: 'lu-circle-check' },
  warning: { color: 'error', icon: 'lu-circle-alert' },
} as const;
