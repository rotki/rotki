/**
 * Checks that every vue-i18n linked message (`@:some.key`) in the locale files resolves.
 *
 * Nothing else catches this. `@intlify/vue-i18n/no-missing-keys` only looks at `t()` call sites in
 * source, never at link targets sitting inside locale values, and `@rotki/no-unused-i18n-keys`
 * builds its linked-key set from the single file being linted, so it can tell you a target is
 * *used* but never that it is *missing*. A link whose target has been deleted lints green and
 * renders the raw `@:some.key` text to the user.
 *
 * That is not hypothetical: `common.rewards` was dropped while `liquity_pools.rewards`
 * ("Unclaimed @:common.rewards", rendered by LiquityPools.vue) still pointed at it. It had two
 * referrers, the other one went away in the same commit, and the survivor was missed. The delete
 * also took the cn/ru/fr translations of the key with it.
 *
 * Resolution walks the fallback chain, verified against vue-i18n 11.4.7: a link is fine when its
 * target exists in its own locale OR in the `en` fallback, so a locale that simply has not
 * translated the target yet is not an error. Only a target missing from BOTH is broken.
 */

import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import process from 'node:process';
import consola from 'consola';

const LOCALES_DIR = '../src/locales';
const FALLBACK_LOCALE = 'en';

/** `@:key`, `@.lower:key`, `@:{'key'}` and `@.lower:{'key'}` — the four linked-message forms. */
const LINKED_MESSAGE = /@(?:\.[a-z]+)?:(?:\{\s*'([^']+)'\s*\}|([\w$.]+))/g;

interface DanglingLink {
  locale: string;
  key: string;
  target: string;
}

type LocaleMessages = Record<string, unknown>;

function isNestedMessages(value: unknown): value is LocaleMessages {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Flattens the nested locale object into `some.dotted.key -> value`, keeping only strings. */
function flatten(messages: LocaleMessages, prefix: string, out: Map<string, string>): Map<string, string> {
  for (const [name, value] of Object.entries(messages)) {
    const key = prefix ? `${prefix}.${name}` : name;
    if (typeof value === 'string')
      out.set(key, value);
    else if (isNestedMessages(value))
      flatten(value, key, out);
  }
  return out;
}

/** Trailing dots are sentence punctuation, not part of the key: "see @:common.rewards." */
function extractLinkTargets(value: string): string[] {
  return Array.from(value.matchAll(LINKED_MESSAGE), match => (match[1] ?? match[2]).replace(/\.+$/, ''));
}

function readLocales(dir: string): Map<string, Map<string, string>> {
  const locales = new Map<string, Map<string, string>>();
  for (const file of readdirSync(dir).filter(name => name.endsWith('.json')).sort()) {
    const parsed: LocaleMessages = JSON.parse(readFileSync(join(dir, file), 'utf-8'));
    locales.set(file.replace(/\.json$/, ''), flatten(parsed, '', new Map()));
  }
  return locales;
}

export function findDanglingLinks(locales: Map<string, Map<string, string>>): DanglingLink[] {
  const fallback = locales.get(FALLBACK_LOCALE);
  if (!fallback)
    throw new Error(`No ${FALLBACK_LOCALE}.json to fall back to`);

  const dangling: DanglingLink[] = [];
  for (const [locale, messages] of locales) {
    for (const [key, value] of messages) {
      for (const target of extractLinkTargets(value)) {
        if (!messages.has(target) && !fallback.has(target))
          dangling.push({ key, locale, target });
      }
    }
  }
  return dangling;
}

// CLI entry point
if (process.argv[1] === import.meta.filename) {
  const dir = join(import.meta.dirname, LOCALES_DIR);
  const locales = readLocales(dir);
  const dangling = findDanglingLinks(locales);
  const linkCount = [...locales.values()]
    .reduce((total, messages) => total + [...messages.values()].reduce((n, value) => n + extractLinkTargets(value).length, 0), 0);

  if (dangling.length === 0) {
    consola.success(`All ${linkCount} linked messages across ${locales.size} locales resolve`);
  }
  else {
    consola.error(`${dangling.length} linked message(s) point at a key that exists in neither the locale nor ${FALLBACK_LOCALE}:`);
    for (const { key, locale, target } of dangling)
      consola.error(`  ${locale}.json  ${key}  ->  @:${target}`);
    consola.error(`Restore the target key, or replace the link with literal text.`);
    process.exit(1);
  }
}
