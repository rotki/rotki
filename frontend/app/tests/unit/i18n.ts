import type { useI18n } from 'vue-i18n';

function stringify(value: Record<string, any>): string {
  return Object.values(value)
    .map(value => value.toString())
    .join(', ');
}

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
