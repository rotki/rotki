import type { DeepReadonly, Ref } from 'vue';
import type { ImportSourceType } from '@/modules/core/common/upload-types';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useLocationTreeApi } from '@/modules/locations/use-location-tree-api';
import { type ImportLocationResolution, useImportDataApi } from '@/modules/user-data/use-import-data-api';

/** The file being imported: a path the backend can read, or the file itself for a web upload. */
type ImportTarget = { readonly path: string } | { readonly file: File };

type LocationMappingOutcome =
  | { readonly proceed: true; readonly mappings: Record<string, string> }
  | { readonly proceed: false; readonly error?: string };

interface UseImportLocationMappingReturn {
  /** The location values the user has to map, while the mapping dialog is open. */
  pending: DeepReadonly<Ref<ImportLocationResolution[] | undefined>>;
  /**
   * Checks the file's location values and, when some are unknown or ambiguous, waits for the user
   * to map them. Resolves to the mappings to import with, or to not importing.
   */
  resolveLocations: (source: ImportSourceType, target: ImportTarget) => Promise<LocationMappingOutcome>;
  confirmMappings: (mappings: Record<string, string>, saveAsAliases: boolean) => void;
  cancelMappings: () => void;
  /** Saves the confirmed mappings as aliases, if the user asked to, once the import succeeded. */
  rememberAliases: () => Promise<void>;
}

function needsMapping(resolution: ImportLocationResolution): boolean {
  return resolution.status !== 'resolved';
}

export function useImportLocationMapping(): UseImportLocationMappingReturn {
  const pending = shallowRef<ImportLocationResolution[]>();
  const aliasesToSave = shallowRef<Record<string, string>>({});
  let settle: ((outcome: LocationMappingOutcome) => void) | undefined;

  const { preflightImport, preflightImportFile } = useImportDataApi();
  const { setLocationAlias } = useLocationTreeApi();

  async function preflight(source: ImportSourceType, target: ImportTarget): Promise<ImportLocationResolution[]> {
    if ('path' in target)
      return preflightImport({ file: target.path, source });
    const data = new FormData();
    data.append('source', source);
    data.append('file', target.file);
    return preflightImportFile(data);
  }

  async function resolveLocations(source: ImportSourceType, target: ImportTarget): Promise<LocationMappingOutcome> {
    set(aliasesToSave, {});
    let resolutions: ImportLocationResolution[];
    try {
      resolutions = await preflight(source, target);
    }
    catch (error: unknown) {
      return { error: getErrorMessage(error), proceed: false };
    }
    const unresolved = resolutions.filter(needsMapping);
    if (unresolved.length === 0)
      return { mappings: {}, proceed: true };

    set(pending, unresolved);
    return new Promise<LocationMappingOutcome>((resolve) => {
      settle = resolve;
    });
  }

  function finish(outcome: LocationMappingOutcome): void {
    set(pending, undefined);
    settle?.(outcome);
    settle = undefined;
  }

  function confirmMappings(mappings: Record<string, string>, saveAsAliases: boolean): void {
    set(aliasesToSave, saveAsAliases ? mappings : {});
    finish({ mappings, proceed: true });
  }

  function cancelMappings(): void {
    finish({ proceed: false });
  }

  async function rememberAliases(): Promise<void> {
    const aliases = Object.entries(get(aliasesToSave));
    set(aliasesToSave, {});
    await Promise.all(aliases.map(async ([alias, location]) => setLocationAlias(alias, location)));
  }

  return {
    cancelMappings,
    confirmMappings,
    pending: readonly(pending),
    rememberAliases,
    resolveLocations,
  };
}
