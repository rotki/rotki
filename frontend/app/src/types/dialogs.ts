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
  info: { icon: 'mdi-information', color: 'primary' },
  warning: { icon: 'mdi-alert-circle', color: 'error' },
  success: { icon: 'mdi-check-circle', color: 'success' }
} as const;
