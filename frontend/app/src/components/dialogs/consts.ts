import { DialogThemes } from '@/components/dialogs/types';

export const TYPE_SUCCESS = 'success';
export const TYPE_WARNING = 'warning';
export const TYPE_INFO = 'info';

export const DIALOG_TYPES = [TYPE_SUCCESS, TYPE_INFO, TYPE_WARNING] as const;

export const themes: DialogThemes = {
  info: { icon: 'mdi-information', color: 'primary' },
  warning: { icon: 'mdi-alert-circle', color: 'error' },
  success: { icon: 'mdi-check-circle', color: 'success' }
};
