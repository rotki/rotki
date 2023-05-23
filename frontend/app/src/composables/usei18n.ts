import { useI18n as i18n } from 'vue-i18n-composable';

export const useI18n = () => {
  const { t: originalT, tc: originalTc, locale } = i18n();

  const t = (
    key: string,
    values?: Record<string, unknown>,
    choice?: number
  ): string => {
    if (choice) {
      return originalTc(key, choice, values);
    }
    return originalT(key, values).toString();
  };

  /**
   * @deprecated use {@link t} as a replacement.
   */
  const tc = (
    key: string,
    choice?: number,
    values?: Record<string, unknown>
  ): string => t(key, values, choice);

  return {
    t,
    tc,
    locale
  };
};
