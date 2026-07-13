import { type Brand, make } from 'plainfp/brand';
import { i18n } from '@/i18n';

/**
 * An i18n message key, branded so it cannot be mistaken for an arbitrary string. Values are produced
 * only by {@link msg.$t}, which the i18n key-usage lint rules recognise as a real usage (a literal
 * argument to a `.$t` call). This keeps keys that are referenced only from static config - such as
 * route `nav` meta, resolved later via `t(key)` - from being reported as unused.
 */
export type MessageKey = Brand<string, 'MessageKey'>;

export const msg = {
  /**
   * Brands an i18n key for use in static config where it cannot be translated eagerly (meta cannot
   * hold reactive translations). Consumers resolve it later with `t(key)`. In dev builds it warns
   * when the key is missing from the loaded messages; the check is dead-code eliminated in
   * production, where `$t` reduces to the identity `make`.
   */
  $t(key: string): MessageKey {
    if (import.meta.env.DEV && import.meta.env.MODE !== 'test' && !i18n.global.te(key))
      console.warn(`[i18n] unknown message key: ${key}`);
    return make<string, 'MessageKey'>(key);
  },
} as const;
