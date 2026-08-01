/**
 * Extracts the identifiers the backend sends for `backend_mappings.*` translation keys.
 *
 * Those keys are built at runtime (`backend_mappings.events.group.${id}`), so the static i18n
 * key-usage rules cannot see them. They used to be silenced with a blanket `backend_mappings.*`
 * entry in the eslint `ignoreKeys` list, which also silenced keys the backend had stopped sending:
 * `backend_mappings.events.type.bridge` survived a rename to `events.group.bridge` and kept the
 * only translation of the label, so several locales quietly fell back to English.
 *
 * Generating the exact key list instead means only keys the backend still emits are ignored, and a
 * key left behind by a rename is reported as unused like any other stale key.
 *
 * Falls back to the committed generated file when the backend directory is unavailable
 * (e.g. Docker builds), mirroring extract-backend-icons.ts.
 */

import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import process from 'node:process';
import consola from 'consola';

const GENERATED_FILE = '../backend-strings.generated.js';

/** Enum members are serialized by `SerializableEnumNameMixin` as lowercased words, and the frontend
 *  snake-cases them back, so the member name maps to the key directly. */
function memberToKey(name: string): string {
  return name.toLowerCase();
}

/** `EventCategoryDetails.label` is free text ("Bridge In"), snake-cased by the frontend. */
function labelToKey(label: string): string {
  return label.trim().toLowerCase().replaceAll(/\s+/g, '_');
}

interface EnumSource {
  file: string;
  enumName: string;
  prefix: string;
}

const ENUM_SOURCES: EnumSource[] = [
  { enumName: 'HistoryEventType', file: 'rotkehlchen/history/events/structures/types.py', prefix: 'backend_mappings.events.history_event_type' },
  { enumName: 'HistoryEventSubType', file: 'rotkehlchen/history/events/structures/types.py', prefix: 'backend_mappings.events.history_event_subtype' },
  { enumName: 'EventCategoryGroup', file: 'rotkehlchen/history/events/structures/types.py', prefix: 'backend_mappings.events.group' },
  { enumName: 'EventDirection', file: 'rotkehlchen/history/events/structures/types.py', prefix: 'backend_mappings.events.type_direction.directions' },
  { enumName: 'AccountingEventType', file: 'rotkehlchen/accounting/mixins/event.py', prefix: 'backend_mappings.profit_loss_event_type' },
  { enumName: 'Location', file: 'rotkehlchen/types.py', prefix: 'backend_mappings.trade_location' },
];

/** Labels come from `EventCategoryDetails(label=...)` rather than the `EventCategory` member name
 *  (BRIDGE_DEPOSIT is labelled "Bridge In"), so they are scraped separately. */
const LABEL_SOURCE = { file: 'rotkehlchen/accounting/constants.py', prefix: 'backend_mappings.events.type' };

/** Keys that are not driven by the backend at all: the exchange sub-lists are hardcoded in the
 *  frontend and `type_direction.title` is a plain static key next to the generated directions. */
const STATIC_KEYS = [
  'backend_mappings.events.type_direction.title',
  'backend_mappings.exchanges.*',
];

function readSource(projectRoot: string, file: string): string | undefined {
  const path = join(projectRoot, file);
  return existsSync(path) ? readFileSync(path, 'utf-8') : undefined;
}

/** Grabs the member names of a single enum: from its `class X(...)` line up to the next top-level
 *  `class`, taking only `NAME = ...` lines indented one level in. */
function extractEnumMembers(content: string, enumName: string): string[] {
  const start = content.search(new RegExp(`^class ${enumName}\\(`, 'm'));
  if (start === -1)
    return [];

  const rest = content.slice(start);
  const nextClass = rest.slice(1).search(/^class /m);
  const body = nextClass === -1 ? rest : rest.slice(0, nextClass + 1);

  return Array.from(body.matchAll(/^ {4}([A-Z][\dA-Z_]*) *=/gm), match => match[1]);
}

function extractCategoryLabels(content: string): string[] {
  return Array.from(content.matchAll(/label='([^']+)'/g), match => match[1]);
}

export function scanBackendKeys(projectRoot: string): { keys: string[]; missingSources: string[] } {
  const keys = new Set<string>();
  const missingSources: string[] = [];

  for (const { enumName, file, prefix } of ENUM_SOURCES) {
    const content = readSource(projectRoot, file);
    if (content === undefined) {
      missingSources.push(file);
      continue;
    }

    const members = extractEnumMembers(content, enumName);
    if (members.length === 0)
      missingSources.push(`${file} (${enumName})`);

    for (const member of members)
      keys.add(`${prefix}.${memberToKey(member)}`);
  }

  const labelContent = readSource(projectRoot, LABEL_SOURCE.file);
  if (labelContent === undefined) {
    missingSources.push(LABEL_SOURCE.file);
  }
  else {
    for (const label of extractCategoryLabels(labelContent))
      keys.add(`${LABEL_SOURCE.prefix}.${labelToKey(label)}`);
  }

  return { keys: [...keys, ...STATIC_KEYS].sort(), missingSources };
}

function getGeneratedFilePath(): string {
  return join(import.meta.dirname, GENERATED_FILE);
}

function generateFileContent(keys: string[]): string {
  const keyList = keys.map(key => `  '${key}',`).join('\n');
  return `/* eslint-disable */
/* prettier-ignore */
// Auto-generated file - DO NOT EDIT MANUALLY
// Generated by scripts/extract-backend-strings.ts
// To regenerate, run: pnpm run generate:backend-strings
// Consumed by eslint.config.js, which is plain ESM and cannot import TypeScript.

export const backendMappingKeys = [
${keyList}
];
`;
}

export function readGeneratedKeys(): string[] {
  const path = getGeneratedFilePath();
  if (!existsSync(path))
    return [];

  const content = readFileSync(path, 'utf-8');
  const match = content.match(/export const backendMappingKeys = \[([\S\s]*?)];/);
  return match ? Array.from(match[1].matchAll(/'([^']+)'/g), m => m[1]) : [];
}

function writeGeneratedFile(keys: string[]): void {
  writeFileSync(getGeneratedFilePath(), generateFileContent(keys), 'utf-8');
  consola.success(`Generated ${GENERATED_FILE} with ${keys.length} keys`);
}

// CLI entry point
if (process.argv[1] === import.meta.filename) {
  const projectRoot = resolve(import.meta.dirname, '../../..');
  const shouldGenerate = process.argv.includes('--generate');
  const { keys, missingSources } = scanBackendKeys(projectRoot);

  if (missingSources.length > 0) {
    consola.error('Could not read these backend sources, so the key list would be incomplete:');
    for (const source of missingSources)
      consola.error(`  - ${source}`);
    process.exit(1);
  }

  consola.info(`Found ${keys.length} backend mapping keys`);

  if (shouldGenerate) {
    writeGeneratedFile(keys);
  }
  else {
    const existing = readGeneratedKeys();
    const added = keys.filter(key => !existing.includes(key));
    const removed = existing.filter(key => !keys.includes(key));

    if (added.length === 0 && removed.length === 0) {
      consola.success(`${GENERATED_FILE} is up to date`);
    }
    else {
      consola.error(`${GENERATED_FILE} is stale. Run: pnpm run generate:backend-strings`);
      for (const key of added)
        consola.error(`  + ${key}`);
      for (const key of removed)
        consola.error(`  - ${key}`);
      process.exit(1);
    }
  }
}
