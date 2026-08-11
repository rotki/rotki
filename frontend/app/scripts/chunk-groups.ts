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

/**
 * Package to chunk assignment. A module under `node_modules/<pkg>/` is placed in the chunk
 * whose list names `<pkg>`.
 */
export const vendorGroups: Record<string, string[]> = {
  'chart': ['echarts', 'vue-echarts'],
  'common': ['@rotki/common', 'bignumber.js'],
  'editor': ['vanilla-jsoneditor'],
  'ui-vendor': ['@rotki/ui-library'],
  'utils': [
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
  'vue-vendor': ['vue', 'vue-router', 'pinia', 'vue-i18n'],
  'wallet-connect': [
    '@walletconnect/core',
    '@walletconnect/universal-provider',
    'viem',
  ],
};

/**
 * Chunks that must never appear in an `index.html` modulepreload. Each is only reachable
 * through a dynamic import, so a preload link means something started importing it statically.
 */
export const lazyChunks: string[] = ['editor', 'wallet-connect'];

/**
 * Misplacements that exist today and are not fixed yet. The check stays green for these but
 * fails on anything new, and it also fails once one of them stops happening, which is the
 * prompt to delete the entry rather than let the list rot.
 *
 * `vue` in `chart`: Rolldown emits the vue runtime into `chart` even though the rule resolves
 * it to `vue-vendor`. Every chunk needs vue, so all of them statically import `chart` and
 * echarts ends up eager. Cause is Rolldown-side and still unknown. This is the big remaining
 * win, worth roughly 257 KB gzip.
 *
 * The `ui-vendor` entries are a few kB each: Rolldown hoists a handful of modules shared with
 * `@rotki/ui-library` into its chunk instead of leaving them in the group they resolve to.
 * Low impact, and it predates the codeSplitting migration.
 */
export const knownViolations: string[] = [
  '@vueuse/core -> ui-vendor (expected utils)',
  '@vueuse/shared -> ui-vendor (expected utils)',
  'dayjs -> ui-vendor (expected utils)',
  'vue -> chart (expected vue-vendor)',
  'vue-router -> ui-vendor (expected vue-vendor)',
];

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

  for (const [chunk, packages] of Object.entries(vendorGroups)) {
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
