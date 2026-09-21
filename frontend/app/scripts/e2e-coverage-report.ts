import type { Profiler } from 'node:inspector';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { mergeScriptCovs } from '@bcoe/v8-coverage';
import { createCoverageMap, type FileCoverage } from '@vitest/istanbul-lib-coverage';
import convert from 'ast-v8-to-istanbul';
import consola from 'consola';
import { parseAstAsync, startVitest } from 'vitest/node';

/**
 * Turns the raw V8 coverage the e2e run collected into `tests/e2e/coverage/lcov.info`, shaped so
 * Codecov can merge it with the unit report.
 *
 * @remarks
 * The run covers the minified preview bundle. Each chunk is converted with the converter
 * `@vitest/coverage-v8` uses for the unit tests, following the chunk's source map back to `src/`.
 * The bundle is still a different compilation from the unit run's per-file one, and Codecov merges
 * reports line by line and matches branches by their position in the file, so the report keeps
 * only what means the same thing on both sides:
 *
 * - files the unit report covers, which also applies its include and exclude lists;
 * - lines only where the unit report has a line, with e2e's own hit counts;
 * - branches only when a file's branch arms are exactly the unit report's;
 * - otherwise no branches, and no hit on a line the unit report has branches for, since Codecov
 *   reads a plain hit merged with a partial line as every branch taken.
 *
 * The unit report's shape comes from a Vitest coverage run that matches no spec: Vitest still
 * compiles every included file to list its lines, the same way it compiles the ones tests load.
 */

const appDir = path.resolve(import.meta.dirname, '..');
const v8CoverageDir = path.join(appDir, 'tests', 'e2e', '.v8-coverage');
const structureDir = path.join(appDir, 'tests', 'e2e', '.unit-structure');
const reportDir = path.join(appDir, 'tests', 'e2e', 'coverage');

/** A spec filter nothing matches, so the coverage run loads no test and only lists the files. */
const NO_SPEC = '__e2e_coverage_structure_only__';

type ScriptCoverage = Pick<Profiler.ScriptCoverage, 'functions' | 'url'>;

/** One arm of a branch in lcov terms: the branch's line, its index in the file (block) and the arm. */
interface BranchRecord {
  line: number;
  block: string;
  arm: number;
  taken: number;
}

/** What the unit report says about a file: its executable lines and the identity of its branch arms. */
interface UnitFile {
  lines: Set<number>;
  branchLines: Set<number>;
  branchArms: Set<string>;
}

/** Line and branch records written for one file. */
interface FileRecords {
  lines: [line: number, hits: number][];
  branches: BranchRecord[];
}

function armKey(line: number, block: string, arm: number): string {
  return `${line},${block},${arm}`;
}

/** Writes the unit report's shape for every included file to `structureDir`, running no test. */
async function writeUnitStructure(): Promise<void> {
  fs.rmSync(structureDir, { force: true, recursive: true });
  const vitest = await startVitest('test', [NO_SPEC], {
    root: appDir,
    run: true,
    watch: false,
    passWithNoTests: true,
    coverage: { enabled: true, reporter: ['lcov'], reportsDirectory: structureDir },
  });
  await vitest.close();
}

/** Adds one `DA` or `BRDA` record of the unit report to the file it belongs to; other records are ignored. */
function addUnitRecord(file: UnitFile, record: string): void {
  if (record.startsWith('DA:')) {
    file.lines.add(Number.parseInt(record.slice(3), 10));
    return;
  }
  if (record.startsWith('BRDA:')) {
    const [line = '', block = '', arm = ''] = record.slice(5).split(',');
    file.branchLines.add(Number.parseInt(line, 10));
    file.branchArms.add(armKey(Number.parseInt(line, 10), block, Number.parseInt(arm, 10)));
  }
}

/** Reads each file's lines and branch arms from the unit structure report, keyed by app-relative path. */
function readUnitStructure(): Map<string, UnitFile> {
  const files = new Map<string, UnitFile>();
  let current: UnitFile | undefined;
  for (const record of fs.readFileSync(path.join(structureDir, 'lcov.info'), 'utf8').split('\n')) {
    if (record.startsWith('SF:')) {
      current = { branchArms: new Set(), branchLines: new Set(), lines: new Set() };
      files.set(record.slice(3), current);
    }
    else if (current) {
      addUnitRecord(current, record);
    }
  }
  return files;
}

/** Whether a parsed file has the shape `tests/e2e/coverage.ts` writes. */
function isSavedCoverage(value: unknown): value is { result: ScriptCoverage[] } {
  return typeof value === 'object' && value !== null && 'result' in value && Array.isArray(value.result);
}

/** Groups every saved V8 result by chunk URL. */
function readV8Coverage(): Map<string, ScriptCoverage[]> {
  const byUrl = new Map<string, ScriptCoverage[]>();
  const saved = fs.existsSync(v8CoverageDir) ? fs.readdirSync(v8CoverageDir) : [];
  for (const file of saved) {
    const parsed: unknown = JSON.parse(fs.readFileSync(path.join(v8CoverageDir, file), 'utf8'));
    if (!isSavedCoverage(parsed))
      throw new Error(`${file} is not a saved e2e coverage file`);

    for (const script of parsed.result)
      byUrl.set(script.url, [...(byUrl.get(script.url) ?? []), script]);
  }
  return byUrl;
}

/**
 * Converts every chunk's coverage to istanbul form on the source files its map names.
 *
 * @remarks
 * A chunk's results from every test are merged in V8 form first, so each chunk is parsed and
 * converted once. The converter finds the map through the chunk's `sourceMappingURL` comment.
 *
 * The chunks have to be the build the coverage was collected from. A plain `test:e2e` and the
 * shard runner build with different backend URLs, so their chunk names differ, and either one
 * replaces the other's `dist/`.
 */
async function convertChunks(byUrl: Map<string, ScriptCoverage[]>): Promise<ReturnType<typeof createCoverageMap>> {
  const coverageMap = createCoverageMap();
  for (const [url, scripts] of byUrl) {
    const merged = mergeScriptCovs(scripts.map(script => ({ ...script, scriptId: '0' })));
    if (!merged)
      continue;

    const chunk = fileURLToPath(url);
    if (!fs.existsSync(chunk))
      throw new Error(`${chunk} is gone: dist/ was rebuilt after this coverage was collected. Clear ${v8CoverageDir} and run the suite again.`);

    const code = fs.readFileSync(chunk, 'utf8');
    coverageMap.merge(await convert({ ast: parseAstAsync(code), code, coverage: { functions: merged.functions, url } }));
  }
  return coverageMap;
}

/** Branch arms the way Vitest's lcov writer numbers them, so they compare equal to the unit report's. */
function branchRecordsOf(coverage: FileCoverage): BranchRecord[] {
  return Object.entries(coverage.b).flatMap(([block, counts]) => {
    const branch = coverage.branchMap[block];
    if (!branch)
      return [];
    return counts.map((taken, arm) => ({ arm, block, line: branch.loc.start.line, taken }));
  });
}

/** Keeps the part of a file's e2e coverage that means the same thing as the unit report's. */
function recordsOnUnitReport(coverage: FileCoverage, unit: UnitFile): FileRecords {
  const branches = branchRecordsOf(coverage);
  const sameBranches = branches.length === unit.branchArms.size
    && branches.every(({ arm, block, line }) => unit.branchArms.has(armKey(line, block, arm)));
  const lines = Object.entries(coverage.getLineCoverage())
    .map(([line, hits]): [number, number] => [Number(line), hits])
    .filter(([line]) => unit.lines.has(line) && (sameBranches || !unit.branchLines.has(line)));
  return { branches: sameBranches ? branches : [], lines };
}

function toLcovRecord(file: string, { branches, lines }: FileRecords): string {
  const sorted = [...lines].sort(([a], [b]) => a - b);
  return [
    `SF:${file}`,
    ...sorted.map(([line, hits]) => `DA:${line},${hits}`),
    `LF:${sorted.length}`,
    `LH:${sorted.filter(([, hits]) => hits > 0).length}`,
    ...branches.map(({ arm, block, line, taken }) => `BRDA:${line},${block},${arm},${taken}`),
    `BRF:${branches.length}`,
    `BRH:${branches.filter(({ taken }) => taken > 0).length}`,
    'end_of_record',
  ].join('\n');
}

const byUrl = readV8Coverage();
if (byUrl.size === 0) {
  consola.error(`No e2e coverage in ${v8CoverageDir}; run the suite with E2E_COVERAGE=true first.`);
  process.exit(1);
}

const coverageMap = await convertChunks(byUrl);
await writeUnitStructure();
const unitFiles = readUnitStructure();

const records: string[] = [];
let lines = 0;
let linesHit = 0;
let filesWithBranches = 0;
for (const absolute of coverageMap.files()) {
  const file = path.relative(appDir, absolute);
  const unit = unitFiles.get(file);
  if (!unit)
    continue;

  const fileRecords = recordsOnUnitReport(coverageMap.fileCoverageFor(absolute), unit);
  lines += fileRecords.lines.length;
  linesHit += fileRecords.lines.filter(([, hits]) => hits > 0).length;
  if (fileRecords.branches.length > 0)
    filesWithBranches += 1;
  records.push(toLcovRecord(file, fileRecords));
}

fs.mkdirSync(reportDir, { recursive: true });
fs.writeFileSync(path.join(reportDir, 'lcov.info'), `${records.join('\n')}\n`);
const percent = lines === 0 ? 0 : (linesHit / lines) * 100;
consola.success(`e2e coverage: ${records.length} files, lines ${linesHit}/${lines} (${percent.toFixed(2)}%), branch data kept for ${filesWithBranches} files`);
