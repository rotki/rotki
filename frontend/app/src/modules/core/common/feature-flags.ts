import type { RouteName } from '@/types/router';

/**
 * Build-time feature flags.
 *
 * The backend gates the accounting refactor behind ROTKI_ACCOUNTING_UPDATE and
 * `vite.config.ts` mirrors that same shell var into VITE_ACCOUNTING_UPDATE, so the
 * frontend never declares a flag of its own. Every surface that has to hide the
 * feature (drawer, search palette, router, dashboard, pinned rail) reads it from
 * here so the gates cannot drift apart.
 *
 * Read through the function rather than a module-level constant: the value is then
 * resolved per call, which keeps `vi.stubEnv` usable in tests.
 */
export function isAccountingUpdateEnabled(): boolean {
  return !!import.meta.env.VITE_ACCOUNTING_UPDATE;
}

/**
 * Routes that only exist in accounting-update builds. Their page files are always
 * compiled in, so the router registers them either way; the global guard turns a
 * direct hit into a redirect when the flag is off.
 */
export const ACCOUNTING_UPDATE_ROUTES: ReadonlySet<string> = new Set<RouteName>([
  '/history/data-issues/',
]);
