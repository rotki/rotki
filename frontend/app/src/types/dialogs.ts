export const DialogType = {
  SUCCESS: 'success',
  WARNING: 'warning',
  INFO: 'info'
} as const;

export type DialogType = (typeof DialogType)[keyof typeof DialogType];

export interface DialogTheme {
  readonly icon: string;
  readonly color: string;
}

export type DialogThemes = { [type in DialogType]: DialogTheme };

export const themes: DialogThemes = {
  info: { icon: 'information-line', color: 'primary' },
  warning: { icon: 'error-warning-line', color: 'error' },
  success: { icon: 'checkbox-circle-line', color: 'success' }
} as const;
