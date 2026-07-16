import fs from 'node:fs';
import { platform } from 'node:os';
import process from 'node:process';

/**
 * Node-only helper: do NOT import this from renderer code. It touches `node:fs`
 * and `node:process`, which the renderer bundle must not pull in. It lives in
 * `shared/` because every `cargo` call site spans three build contexts - the dev
 * scripts (`frontend/scripts`), the app scripts (`frontend/app/scripts`) and the
 * vite-bundled electron main - and this is the only directory all three reach.
 */

const STRAWBERRY_PATHS: string[] = [
  'C:\\Strawberry\\perl\\bin',
  'C:\\Strawberry\\perl\\site\\bin',
  'C:\\Strawberry\\c\\bin',
];

/**
 * Mirrors `__get_windows_cargo_env` in `package.py`: when colibri builds on
 * Windows, `rusqlite`'s `bundled-sqlcipher-vendored-openssl` feature compiles
 * OpenSSL from source, whose Configure script is a Perl script. Git for
 * Windows ships a mingw64 Perl that mishandles string interpolation in OpenSSL's
 * Configure (e.g. eats `$M` from `SYS$MANAGER:[OPENSSL]`), making the build fail
 * with a cryptic `Number found where operator expected` error. Strawberry Perl
 * handles this correctly, so we prepend it on PATH.
 *
 * Prepending (rather than stripping the mingw Perl) is deliberate: PATH lookup is
 * first-match, so Strawberry winning is sufficient, and it keeps this in step with
 * `package.py` - those two must not drift.
 *
 * Important: Windows env is case-insensitive, but Node spawns children with the
 * literal keys you pass. If we add `PATH` while `process.env` still has `Path`,
 * the child receives both and which one wins is undefined - the original Git Perl
 * keeps winning. We must replace the existing key in place (not add a
 * duplicate-cased one), which is why this returns a COMPLETE env rather than an
 * overlay to be spread over `process.env`.
 *
 * Returns undefined on POSIX (caller should inherit `process.env` untouched), or
 * null on Windows when Strawberry isn't installed (caller decides whether to
 * warn/abort).
 */
export function buildCargoEnv(): Record<string, string> | null | undefined {
  if (platform() !== 'win32')
    return undefined;

  const existing = STRAWBERRY_PATHS.filter(p => fs.existsSync(p));
  if (existing.length === 0)
    return null;

  const merged: Record<string, string> = {};
  let pathKey = 'Path';
  for (const [key, value] of Object.entries(process.env)) {
    if (value === undefined)
      continue;
    if (key.toUpperCase() === 'PATH') {
      pathKey = key;
      continue;
    }
    merged[key] = value;
  }
  const currentPath = process.env.Path ?? process.env.PATH ?? '';
  const parts = currentPath.split(';').filter(p => p && !existing.includes(p));
  merged[pathKey] = [...existing, ...parts].join(';');
  return merged;
}

/** Shared wording so every cargo call site reports a missing Strawberry the same way. */
export const STRAWBERRY_MISSING_WARNING
  = 'Strawberry Perl not found at C:\\Strawberry - the vendored OpenSSL build will likely fail. '
    + 'Install Strawberry Perl from https://strawberryperl.com and re-run.';
