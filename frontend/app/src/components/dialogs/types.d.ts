import { DIALOG_TYPES } from '@/components/dialogs/consts';

export type DialogType = typeof DIALOG_TYPES[number];

export interface DialogTheme {
  readonly icon: string;
  readonly color: string;
}

export type DialogThemes = { [type in DialogType]: DialogTheme };
