import type { useI18n } from 'vue-i18n';

function stringify(value: Record<string, any>): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

/**
 * Echoes a translation key back instead of translating it, so a spec can assert on the key.
 *
 * @remarks
 * A key given interpolation or pluralization arguments comes back as `key::a, b`, the values joined
 * by commas after a `::`. Assert on that whole string rather than on the key alone, since a
 * `toContain` check passes whether or not the arguments arrived.
 *
 * @param key - the translation key, echoed verbatim
 * @param args - interpolation or pluralization values; absent leaves the key bare
 * @returns the key, suffixed with the stringified arguments when there are any
 */
export function mockT(key: any, args?: any) {
  return args ? `${key}::${stringify(args)}` : key;
}

/**
 * `mockT` typed as the vue-i18n `t` function for callers that take the real
 * translate signature. The overloaded `ComposerTranslation` type cannot be
 * satisfied by a plain function, so the single cast is contained here.
 */
// eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- ComposerTranslation is an overloaded interface no plain function can structurally match; contained to this helper
export const mockTranslate = mockT as unknown as ReturnType<typeof useI18n>['t'];
