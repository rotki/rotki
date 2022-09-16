export const TYPE_SUCCESS = 'success';
export const TYPE_WARNING = 'warning';
export const TYPE_INFO = 'info';

export const DIALOG_TYPES = [TYPE_SUCCESS, TYPE_INFO, TYPE_WARNING] as const;

export type DialogType = typeof DIALOG_TYPES[number];

export interface DialogTheme {
  readonly icon: string;
  readonly color: string;
}

export type DialogThemes = { [type in DialogType]: DialogTheme };

export const themes: DialogThemes = {
  info: { icon: 'mdi-information', color: 'primary' },
  warning: { icon: 'mdi-alert-circle', color: 'error' },
  success: { icon: 'mdi-check-circle', color: 'success' }
};
