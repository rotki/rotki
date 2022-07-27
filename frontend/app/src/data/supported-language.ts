import { ActionDataEntry } from '@/store/types';
import { SupportedLanguage } from '@/types/frontend-settings';

export const supportedLanguages: ActionDataEntry<SupportedLanguage>[] = [
  {
    identifier: SupportedLanguage.EN,
    label: 'English'
  },
  {
    identifier: SupportedLanguage.ES,
    label: 'Spanish'
  }
];
