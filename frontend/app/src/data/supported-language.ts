import { SupportedLanguage } from '@/types/settings/frontend-settings';

export const supportedLanguages = [
  {
    countries: ['gb', 'us'],
    identifier: SupportedLanguage.EN,
    label: 'English',
  },
  {
    countries: ['es'],
    identifier: SupportedLanguage.ES,
    label: 'Spanish (Español)',
  },
  {
    countries: ['gr'],
    identifier: SupportedLanguage.GR,
    label: 'Greek (Ελληνικά)',
  },
  {
    countries: ['de'],
    identifier: SupportedLanguage.DE,
    label: 'German (Deutsch)',
  },
  {
    countries: ['cn'],
    identifier: SupportedLanguage.CN,
    label: 'Chinese (中文)',
  },
  {
    countries: ['fr'],
    identifier: SupportedLanguage.FR,
    label: 'French (Français)',
  },
];
