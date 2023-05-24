import { useI18n as i18n } from 'vue-i18n-composable';

type NamedValues = Record<string, unknown>;

interface MigrationTranslator {
  <Key extends string>(key: Key): string;
  <Key extends string>(key: Key, plural: number): string;
  <Key extends string>(key: Key, values: NamedValues): string;
  <Key extends string>(key: Key, values: NamedValues, plural: number): string;
}
interface MigrationI18n {
  locale: Ref<string>;
  t: MigrationTranslator;
  te: <Key extends string>(key: Key) => boolean;
}

export const useI18n = (): MigrationI18n => {
  const { t: originalT, tc: originalTc, locale, te } = i18n();

  const t = <Key extends string>(
    key: Key,
    valuesOrPlural?: NamedValues | number,
    plural?: number
  ): string => {
    if (typeof valuesOrPlural === 'number') {
      return originalTc(key, valuesOrPlural);
    }

    if (plural) {
      return originalTc(key, plural, valuesOrPlural);
    }

    return originalT(key, valuesOrPlural).toString();
  };

  return {
    t,
    te,
    locale
  };
};
