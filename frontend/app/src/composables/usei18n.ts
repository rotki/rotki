import Vue from 'vue';
import type { VueI18n } from 'vue-i18n-bridge';

type NamedValues = Record<string, unknown>;

interface MigrationTranslator {
  <Key extends string>(key: Key): string;
  <Key extends string>(key: Key, plural: number): string;
  <Key extends string>(key: Key, values: NamedValues): string;
  <Key extends string>(key: Key, values: NamedValues, plural: number): string;
}

interface ModifiedI18n extends Omit<VueI18n, 't' | 'locale'> {
  locale: WritableComputedRef<string>;
  t: MigrationTranslator;
}

export function useI18n(): ModifiedI18n {
  const instance = getCurrentInstance();
  const vm = instance?.proxy || new Vue();

  // @ts-expect-error
  return vm._i18nBridgeRoot.global as VueI18n & {
    locale: WritableComputedRef<string>;
  };
}
