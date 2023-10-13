import { SupportedLanguage } from '@/types/settings/frontend-settings';

export const supportedLanguages = [
  {
    identifier: SupportedLanguage.EN,
    label: 'English',
    countries: ['gb', 'us']
  },
  {
    identifier: SupportedLanguage.ES,
    label: 'Spanish (Español)',
    countries: ['es']
  },
  {
    identifier: SupportedLanguage.GR,
    label: 'Greek (Ελληνικά)',
    countries: ['gr']
  },
  {
    identifier: SupportedLanguage.DE,
    label: 'German (Deutsch)',
    countries: ['de']
  },
  {
    identifier: SupportedLanguage.CN,
    label: 'Chinese (中文)',
    countries: ['cn']
  }
];
