#!/usr/bin/env node

/**
 * Bundle placement regression check.
 *
 * Asserts *where* modules land, not how big anything is: a lazy chunk costs nothing however
 * big it gets, while one wrongly-placed helper module drags a whole lazy chunk into the eager
 * startup graph.
 *
 * It runs the renderer build in-process because it needs the module to chunk map, which the
 * production bundle does not carry (no sourcemaps) and cannot be recovered from `dist/`.
 */

import process from 'node:process';
import consola from 'consola';
import { build } from 'vite';
import {
  expectedChunkFor,
  HELPERS_CHUNK,
  knownViolations,
  lazyChunks,
  packageNameFor,
} from './chunk-groups';
import { sharedConfig } from './setup';

process.env.NODE_ENV = 'production';

interface Chunk {
  name: string;
  fileName: string;
  moduleIds: string[];
}

interface Bundle {
  chunks: Chunk[];
  html: string | undefined;
}

function isChunkLike(value: unknown): value is { type: string; name?: string; fileName: string; modules?: Record<string, unknown> } {
  return typeof value === 'object' && value !== null && 'type' in value && 'fileName' in value;
}

function textOf(source: unknown): string | undefined {
  if (typeof source === 'string')
    return source;
  if (source instanceof Uint8Array)
    return new TextDecoder().decode(source);
  return undefined;
}

/**
 * Flattens whatever `vite.build` returned into the chunks plus the emitted `index.html`.
 * The return type is a union of single output, output array, and watcher, so it is narrowed
 * structurally rather than asserted.
 */
function collectBundle(result: unknown): Bundle {
  const outputs: unknown[] = [];
  const visit = (value: unknown): void => {
    if (Array.isArray(value)) {
      value.forEach(visit);
      return;
    }
    if (typeof value === 'object' && value !== null && 'output' in value) {
      visit(Reflect.get(value, 'output'));
      return;
    }
    outputs.push(value);
  };
  visit(result);

  const chunks: Chunk[] = [];
  let html: string | undefined;

  for (const item of outputs) {
    if (!isChunkLike(item))
      continue;

    if (item.type === 'chunk') {
      chunks.push({
        name: item.name ?? item.fileName,
        fileName: item.fileName,
        moduleIds: Object.keys(item.modules ?? {}),
      });
    }
    else if (item.fileName.endsWith('index.html')) {
      html = textOf(Reflect.get(item, 'source'));
    }
  }

  return { chunks, html };
}

/** A package lands in a chunk other than the one the shared rules assign it. */
function checkOwnership(chunks: Chunk[]): string[] {
  // Keyed by "<package> -> <actual>" so a package split across chunks reports once per chunk
  // rather than once per module.
  const violations = new Set<string>();

  for (const chunk of chunks) {
    for (const id of chunk.moduleIds) {
      const expected = expectedChunkFor(id);
      if (!expected || expected === chunk.name)
        continue;

      const owner = packageNameFor(id) ?? id;
      violations.add(`${owner} -> ${chunk.name} (expected ${expected})`);
    }
  }

  return [...violations].sort();
}

/** A chunk that should only ever be reached by dynamic import is preloaded at startup. */
function checkLaziness(chunks: Chunk[], html: string | undefined): string[] {
  if (html === undefined)
    return ['index.html was not emitted, cannot verify the eager startup graph'];

  const byFileName = new Map(chunks.map(chunk => [chunk.fileName, chunk.name]));
  const preloaded = new Set<string>();

  for (const match of html.matchAll(/<link[^>]+rel="modulepreload"[^>]*>/g)) {
    const href = /href="([^"]+)"/.exec(match[0])?.[1];
    if (!href)
      continue;
    const name = byFileName.get(href.replace(/^\.?\//, ''));
    if (name)
      preloaded.add(name);
  }

  // A script tag counts too: it is the entry's own static graph.
  for (const match of html.matchAll(/<script[^>]+src="([^"]+)"[^>]*>/g)) {
    const name = byFileName.get(match[1].replace(/^\.?\//, ''));
    if (name)
      preloaded.add(name);
  }

  return lazyChunks
    .filter(name => preloaded.has(name))
    .map(name => `${name} is in the eager startup graph (index.html preloads it)`);
}

/** The helpers chunk must exist, or the virtual helper ids have drifted and nothing is pinned. */
function checkHelpersChunk(chunks: Chunk[]): string[] {
  const helpers = chunks.find(chunk => chunk.name === HELPERS_CHUNK);
  if (!helpers)
    return [`no "${HELPERS_CHUNK}" chunk was emitted; the injected helper module ids in chunk-groups.ts have probably changed`];
  if (helpers.moduleIds.length === 0)
    return [`the "${HELPERS_CHUNK}" chunk is empty`];
  return [];
}

async function run(): Promise<void> {
  consola.info('Building the renderer to inspect chunk placement...');

  const result = await build({
    ...sharedConfig,
    mode: 'production',
    configFile: 'vite.config.ts',
    logLevel: 'warn',
    // Never touch dist/: the CI Build step's artifact must survive this check.
    build: { write: false },
    plugins: [{ name: 'check-bundle' }],
  });

  const { chunks, html } = collectBundle(result);
  if (chunks.length === 0) {
    consola.error('The build produced no chunks.');
    process.exit(1);
  }

  const hard = [...checkHelpersChunk(chunks), ...checkLaziness(chunks, html)];
  const ownership = checkOwnership(chunks);

  const known = new Set(knownViolations);
  const unexpected = ownership.filter(violation => !known.has(violation));
  const healed = [...known].filter(violation => !ownership.includes(violation));

  if (ownership.some(violation => known.has(violation))) {
    consola.warn(`Known misplacements, tracked in chunk-groups.ts:\n${ownership.filter(v => known.has(v)).map(v => `  - ${v}`).join('\n')}`);
  }

  const failures = [
    ...hard,
    ...unexpected.map(violation => `new misplacement: ${violation}`),
    ...healed.map(violation => `known misplacement no longer happens, remove it from knownViolations: ${violation}`),
  ];

  if (failures.length > 0) {
    consola.error(`Bundle placement check failed:\n${failures.map(failure => `  - ${failure}`).join('\n')}`);
    process.exit(1);
  }

  consola.success(`Bundle placement is intact (${chunks.length} chunks, ${lazyChunks.join(' and ')} stayed lazy).`);
  process.exit(0);
}

try {
  await run();
}
catch (error) {
  consola.error(error);
  process.exit(1);
}
