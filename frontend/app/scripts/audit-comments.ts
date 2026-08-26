/**
 * Two questions about comments, asked across the tree so a reviewer reads a shortlist rather than
 * every comment in it: which ones are probably not worth keeping, and which exported functions
 * carry no contract at all.
 *
 * @remarks
 * Every rule here is a heuristic, and the output is a reading list rather than a delete list. The
 * decision stays what it always was: breaking the code a comment describes has to fail a named
 * test, and the code must not already say it.
 *
 * `undocumented` is the other half. Deleting a comment because a test enforces it only holds if
 * the behaviour still reads off the function itself, so an exported function with no TSDoc is
 * where a contract went missing rather than where prose was saved.
 *
 * Usage, from `frontend/`:
 * ```
 * pnpm run audit:comments                     # everything
 * pnpm run audit:comments -- --kind=history   # one class
 * pnpm run audit:comments -- --specs          # spec files only
 * pnpm run audit:comments -- app/src/modules/balances
 * ```
 *
 * @packageDocumentation
 */

import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import process from 'node:process';

interface Finding {
  file: string;
  line: number;
  kind: string;
  text: string;
}

/** Runs from `frontend/` or `frontend/app/` depending on the caller, so the tree is found, not assumed. */
const ROOT = ['src', 'app/src'].find(candidate => existsSync(candidate)) ?? 'src';

/**
 * "Used to" is ambiguous. History reads `<subject> used to <verb>`; purpose reads `, used to
 * <verb>` or `is used to <verb>`, and neither is about the past. Only the first is matched: a
 * lowercase word in front, but not a comma and not a copula.
 */
const HISTORY = /(?<!\bis\s)(?<!\bare\s)(?<!\bbe\s)(?<!\bbeing\s)(?<!\bbeen\s)(?<=[a-z]\s)used to\b|\b(?:previously|no longer|before this|has been replaced)\b|\bnow that\b/i;
const FILEREF = /[a-z0-9_-]+\.(?:ts|py|vue):\d+|§\d/;
const BANNER = /^\/\/\s*[-=*]{3,}|^\/\/\s*(?:mock|setup|helpers?|constants?|types?|imports?)\b[\w\s]*$/i;
const NARRATION = /^\/\/\s*[A-Z][\w' ]{0,40}$/;
const EXPORTED_FN = /^export (?:async )?function (\w+)|^export const (\w+) = (?:async )?(?:\([^)]*\)|function)/;

const STOPWORDS = new Set([
  'a',
  'an',
  'and',
  'are',
  'as',
  'at',
  'be',
  'but',
  'by',
  'do',
  'does',
  'for',
  'from',
  'has',
  'in',
  'is',
  'it',
  'its',
  'not',
  'of',
  'on',
  'or',
  'so',
  'that',
  'the',
  'then',
  'this',
  'to',
  'until',
  'we',
  'when',
  'with',
]);

const BLURB: Record<string, string> = {
  duplicate: 'a test whose body matches another in the same file. One of the two is dead weight',
  banner: 'a section divider; the declaration below is the label',
  fileref: 'names a file:line or a section number that drifts - verify it, then name a symbol instead',
  history: 'describes what the code USED to do. Nothing fails when a narrative stops being true, so read every one',
  narration: 'narrates the statement below it',
  hoist: 'explains behaviour from inside a function body. Behaviour belongs in TSDoc on the signature',
  restates: 'its own words already appear in the code beneath it',
  undocumented: 'exported, with no TSDoc. If a comment was deleted here, the contract went with it',
};

const ORDER = ['duplicate', 'history', 'fileref', 'undocumented', 'hoist', 'restates', 'narration', 'banner'];

function walk(dir: string, out: string[] = []): string[] {
  if (!statSync(dir).isDirectory())
    return /\.(?:ts|vue)$/.test(dir) ? [dir] : [];

  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory())
      walk(full, out);
    else if (/\.(?:ts|vue)$/.test(entry))
      out.push(full);
  }
  return out;
}

function words(value: string): string[] {
  return value.toLowerCase().match(/[a-z][a-z0-9]{2,}/g)?.filter(word => !STOPWORDS.has(word)) ?? [];
}

/** Whether a comment's own vocabulary already appears in the code it sits above. */
function restatesCode(comment: string, code: string): boolean {
  const terms = words(comment);
  if (terms.length < 2 || terms.length > 9)
    return false;

  const target = code.toLowerCase();
  return terms.filter(term => target.includes(term)).length / terms.length >= 0.6;
}

function nextCode(lines: string[], from: number): string {
  for (let i = from; i < Math.min(from + 3, lines.length); i++) {
    const line = lines[i].trim();
    if (line && !line.startsWith('//') && !line.startsWith('*') && !line.startsWith('/*'))
      return line;
  }
  return '';
}

/** Classes a `//` line can fall into once the content rules have all missed. */
function classifyLineComment(lines: string[], index: number, text: string): string | undefined {
  // A continuation line is judged by the run it belongs to, not on its own.
  if (lines[index - 1]?.trim().startsWith('//'))
    return undefined;

  const code = nextCode(lines, index + 1);
  if (code && restatesCode(text.replace(/^\/\/\s*/, ''), code))
    return 'restates';
  if (NARRATION.test(text))
    return 'narration';

  // Indented, so inside a body rather than above a declaration, and long enough to be an
  // explanation rather than a label.
  const indented = /^\s{4,}\/\//.test(lines[index]);
  return indented && text.length > 60 ? 'hoist' : undefined;
}

function classifyComment(lines: string[], index: number): string | undefined {
  const text = lines[index].trim();
  const isLine = text.startsWith('//');
  if (!isLine && !text.startsWith('*') && !text.startsWith('/**'))
    return undefined;

  if (isLine && BANNER.test(text))
    return 'banner';
  if (FILEREF.test(text))
    return 'fileref';
  if (HISTORY.test(text))
    return 'history';

  return isLine ? classifyLineComment(lines, index, text) : undefined;
}

/** An exported function whose preceding line is not the close of a doc block. */
function undocumentedExport(lines: string[], index: number): string | undefined {
  const match = EXPORTED_FN.exec(lines[index]);
  if (!match)
    return undefined;

  const above = lines[index - 1]?.trim() ?? '';
  if (above.endsWith('*/'))
    return undefined;

  return match[1] ?? match[2];
}

interface OpenTest {
  line: number;
  name: string;
  body: string[];
}

/** Net brace depth a line adds, which is how the end of a test body is found. */
function braceDelta(line: string): number {
  return (line.match(/\{/g)?.length ?? 0) - (line.match(/\}/g)?.length ?? 0);
}

/** Every `it(...)` in a file, paired with the body it opened. */
function readTests(lines: string[]): OpenTest[] {
  const tests: OpenTest[] = [];
  let open: OpenTest | undefined;
  let depth = 0;

  for (const [index, line] of lines.entries()) {
    const start = /^\s*it(?:\.\w+)?\('([^']+)'/.exec(line);
    if (start && !open)
      open = { body: [], line: index + 1, name: start[1] };

    if (!open)
      continue;

    // Only a whole-line comment is dropped. Stripping from any `//` would truncate a url literal.
    const trimmed = line.trim();
    open.body.push(trimmed.startsWith('//') ? '' : trimmed);
    depth = start ? braceDelta(line) : depth + braceDelta(line);

    if (open.body.length > 1 && depth <= 0) {
      tests.push(open);
      open = undefined;
    }
  }
  return tests;
}

/**
 * Tests in one file whose bodies are identical.
 *
 * @remarks
 * Two tests asserting the same thing under different names do not double the confidence, they
 * double what has to be kept true, and one of the names is usually lying about what it covers.
 * Only exact twins are reported, so a near-copy is missed rather than a distinct test accused.
 */
function duplicateTests(lines: string[]): Finding[] {
  const bodies = new Map<string, OpenTest>();
  const findings: Finding[] = [];

  for (const test of readTests(lines)) {
    // Joined with newlines rather than stripped of whitespace, so two calls differing only inside
    // a string literal (`''` against `'   '`) stay distinct.
    const key = test.body.slice(1).join('\n');
    if (key.length <= 40)
      continue;

    const twin = bodies.get(key);
    if (twin)
      findings.push({ file: '', kind: 'duplicate', line: test.line, text: `${test.name} — same body as "${twin.name}" at line ${twin.line}` });
    else
      bodies.set(key, test);
  }
  return findings;
}

function collect(files: string[]): Finding[] {
  const findings: Finding[] = [];
  for (const file of files) {
    const lines = readFileSync(file, 'utf8').split('\n');
    const name = relative(ROOT, file);

    if (file.endsWith('.spec.ts'))
      findings.push(...duplicateTests(lines).map(finding => ({ ...finding, file: name })));

    for (let i = 0; i < lines.length; i++) {
      const kind = classifyComment(lines, i);
      if (kind) {
        findings.push({ file: name, kind, line: i + 1, text: lines[i].trim() });
        continue;
      }

      const exported = undocumentedExport(lines, i);
      if (exported && !file.endsWith('.spec.ts'))
        findings.push({ file: name, kind: 'undocumented', line: i + 1, text: exported });
    }
  }
  return findings;
}

const args = process.argv.slice(2);
const only = args.find(arg => arg.startsWith('--kind='))?.slice('--kind='.length);

/** Accepts a path written from `frontend/` or from `frontend/app/`, so neither caller has to guess. */
function resolveScope(given: string | undefined): string {
  if (!given)
    return ROOT;
  if (existsSync(given))
    return given;

  const alternatives = [given.replace(/^app\//, ''), join('app', given), join(ROOT, given)];
  return alternatives.find(candidate => existsSync(candidate)) ?? given;
}

const scope = resolveScope(args.find(arg => !arg.startsWith('--')));

let files = walk(scope);
if (args.includes('--specs'))
  files = files.filter(file => file.endsWith('.spec.ts'));
if (args.includes('--source'))
  files = files.filter(file => !file.endsWith('.spec.ts'));

const findings = collect(files).filter(finding => !only || finding.kind === only);
const byKind = new Map<string, Finding[]>();
for (const finding of findings)
  byKind.set(finding.kind, [...byKind.get(finding.kind) ?? [], finding]);

for (const kind of ORDER) {
  const group = byKind.get(kind);
  if (!group?.length)
    continue;

  console.log(`\n${kind.toUpperCase()}  (${group.length})  ${BLURB[kind]}`);
  for (const finding of group)
    console.log(`  ${finding.file}:${finding.line}  ${finding.text.slice(0, 100)}`);
}

console.log(`\n${findings.length} flagged across ${new Set(findings.map(item => item.file)).size} files.`);
console.log('Heuristics, not verdicts. Keep whatever a naive edit would silently break.');
