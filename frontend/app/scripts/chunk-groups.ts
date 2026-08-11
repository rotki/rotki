/**
 * Chunk placement rules, shared by `vite.config.ts` and `check:bundle` so the build and its
 * regression check cannot drift apart.
 *
 * The rules assert *placement*, not size. A lazy chunk costs nothing however big it is; what
 * costs is a chunk being pulled into the eager startup graph by a static import.
 */

/** Chunk that collects the injected helper modules. */
export const HELPERS_CHUNK = 'helpers';

/**
 * Virtual helper modules Vite and Rolldown inject into the graph.
 *
 * They are not real files, so `manualChunks` never sees them. Left unassigned, Rolldown parks
 * each one in whichever big lazy chunk claims it first, and every importer of that helper then
 * statically imports the whole chunk, dragging it into the eager startup graph. Pinning them to
 * one tiny `helpers` chunk is what keeps `editor` and `wallet-connect` lazy.
 */
export const sharedHelperModules = new Set<string>([
  '\0plugin-vue:export-helper',
  '\0rolldown_dynamic_import_helper.js',
  '\0vite/modulepreload-polyfill.js',
  '\0vite/preload-helper.js',
]);

export interface VendorGroup {
  chunk: string;
  priority: number;
  packages: string[];
}

/**
 * Package to chunk assignment, highest priority first. A module under `node_modules/<pkg>/`
 * is placed in the chunk whose list names `<pkg>`.
 *
 * **Priority is load-bearing, not cosmetic.** Rolldown lets the highest-priority matching
 * group claim a module and removes it from the others, and a widely shared dependency that
 * the wrong group claims drags that whole group into the eager startup graph. `vue-vendor`
 * ranks above everything because every chunk needs the vue runtime: while `chart` outranked
 * it, vue was emitted into `chart`, so all 369 chunks statically imported `chart` and echarts
 * loaded at startup. Raising `vue-vendor` is what makes `chart` lazy.
 */
export const vendorGroups: VendorGroup[] = [
  { chunk: 'vue-vendor', priority: 90, packages: ['vue', 'vue-router', 'pinia', 'vue-i18n'] },
  { chunk: 'common', priority: 80, packages: ['@rotki/common', 'bignumber.js'] },
  {
    chunk: 'utils',
    priority: 70,
    packages: [
      '@vueuse/math',
      '@vueuse/core',
      '@vueuse/shared',
      '@vuelidate/core',
      '@vuelidate/validators',
      'ofetch',
      'es-toolkit',
      'imask',
      'dayjs',
      'consola',
      'zod',
    ],
  },
  { chunk: 'ui-vendor', priority: 60, packages: ['@rotki/ui-library'] },
  { chunk: 'chart', priority: 50, packages: ['echarts', 'vue-echarts'] },
  { chunk: 'editor', priority: 40, packages: ['vanilla-jsoneditor'] },
  {
    chunk: 'wallet-connect',
    priority: 30,
    packages: ['@walletconnect/core', '@walletconnect/universal-provider', 'viem'],
  },
];

/**
 * The vendor groups as one explicit `test` + `priority` entry per chunk. A single group with
 * a shared dynamic `name()` cannot express the ordering above, because every name it returns
 * gets the same priority.
 */
export function vendorGroupEntries(): { name: string; priority: number; test: (id: string) => boolean }[] {
  return vendorGroups.map(({ chunk, priority, packages }) => ({
    name: chunk,
    priority,
    test: (id: string): boolean => {
      const pkg = packageOf(id);
      return pkg !== undefined && packages.includes(pkg);
    },
  }));
}

/**
 * Chunks that must never appear in an `index.html` modulepreload. Each is only reachable
 * through a dynamic import, so a preload link means something started importing it statically.
 */
export const lazyChunks: string[] = ['chart', 'editor', 'wallet-connect'];

/**
 * Misplacements that exist today and are not fixed yet. The check stays green for these but
 * fails on anything new, and it also fails once one of them stops happening, which is the
 * prompt to delete the entry rather than let the list rot.
 *
 * Empty on purpose: every package currently lands where the rules say it should. Add an entry
 * only to record a misplacement you are deliberately not fixing.
 */
export const knownViolations: string[] = [];

function packageOf(id: string): string | undefined {
  const normalized = id.replaceAll('\\', '/');
  const marker = '/node_modules/';
  const index = normalized.lastIndexOf(marker);
  if (index === -1)
    return undefined;

  const rest = normalized.slice(index + marker.length);
  const parts = rest.split('/');
  if (parts.length < 2)
    return undefined;

  return parts[0].startsWith('@') ? `${parts[0]}/${parts[1]}` : parts[0];
}

/**
 * Chunk a module belongs to, or `null` to leave the decision to Rolldown.
 */
export function vendorChunkFor(id: string): string | null {
  const pkg = packageOf(id);
  if (!pkg)
    return null;

  for (const { chunk, packages } of vendorGroups) {
    if (packages.includes(pkg))
      return chunk;
  }
  return null;
}

/**
 * Chunk a module is *expected* to land in, covering helpers as well as vendors.
 */
export function expectedChunkFor(id: string): string | null {
  if (sharedHelperModules.has(id))
    return HELPERS_CHUNK;
  return vendorChunkFor(id);
}

/** The owning package of a module, for reporting a violation in terms a reader can act on. */
export function packageNameFor(id: string): string | undefined {
  return packageOf(id);
}
