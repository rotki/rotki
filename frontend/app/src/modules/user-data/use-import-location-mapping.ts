import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { ImportSourceType } from '@/modules/core/common/upload-types';
import type { ImportLocationResolution } from '@/modules/user-data/import-location-types';
import { startPromise } from '@shared/utils';
import { useLocationAliases } from '@/modules/locations/use-location-aliases';
import { useImportDataApi } from '@/modules/user-data/use-import-data-api';

/** The file being imported: a path the backend can read, or the upload a web build sends. */
type ImportTarget = { readonly path: string } | { readonly formData: FormData };

/**
 * What a location check found: every value placed, some left for the user to map, or nothing,
 * because another file was picked while it ran.
 */
type LocationCheck = 'placed' | 'unplaced' | 'replaced';

interface UseImportLocationMappingReturn {
  /** The location values the last check could not place, which the user has to map. */
  pending: ComputedRef<DeepReadonly<ImportLocationResolution>[]>;
  /** The location the user chose for each value that did not resolve. */
  modelMappings: Ref<Record<string, string>>;
  /** Whether the chosen locations are kept as aliases once the import succeeds. */
  modelSaveAsAliases: Ref<boolean>;
  /** Whether a pending value still has no location chosen for it. */
  choicesMissing: ComputedRef<boolean>;
  /**
   * Checks how the file's location values resolve with the mappings chosen so far.
   *
   * @remarks
   * A check that ends after `reset()` is dropped, so the values of a file the user replaced
   * never show against, or hold back, the file picked after it.
   */
  checkLocations: (source: ImportSourceType, target: ImportTarget) => Promise<LocationCheck>;
  /**
   * Saves the chosen locations as aliases, if the user asked to, without waiting; the import
   * already succeeded, so the aliases that could not be saved are only handed to `onFailure`.
   */
  rememberAliases: (onFailure: (failed: string) => void) => void;
  /** Forgets the check and the choices, for the next file. */
  reset: () => void;
}

/** The location values of a CSV import that need the user to choose where their rows go. */
export function useImportLocationMapping(): UseImportLocationMappingReturn {
  const resolutions = shallowRef<ImportLocationResolution[]>([]);
  const modelMappings = ref<Record<string, string>>({});
  const modelSaveAsAliases = shallowRef<boolean>(true);
  /** Bumped by every reset, so a check can tell its file was replaced while it ran. */
  let generation = 0;

  const { checkImportFileLocations, checkImportLocations } = useImportDataApi();
  const { saveAlias } = useLocationAliases();

  const pending = computed<DeepReadonly<ImportLocationResolution>[]>(() =>
    get(resolutions).filter(entry => entry.status !== 'resolved'),
  );

  const choicesMissing = computed<boolean>(() => {
    const mappings = get(modelMappings);
    return get(pending).some(entry => !mappings[entry.value]);
  });

  async function checkLocations(source: ImportSourceType, target: ImportTarget): Promise<LocationCheck> {
    const started = generation;
    const found = 'path' in target
      ? await checkImportLocations({ file: target.path, locationMappings: get(modelMappings), source })
      : await checkImportFileLocations(target.formData);
    if (started !== generation)
      return 'replaced';
    set(resolutions, found);
    return get(pending).length === 0 ? 'placed' : 'unplaced';
  }

  /**
   * Saves every chosen location under its value; an empty value can not be an alias.
   *
   * @remarks
   * Each alias is saved on its own, so one failure does not hide which of the others were kept:
   * `onFailure` gets only the aliases that failed, each with its reason.
   */
  function rememberAliases(onFailure: (failed: string) => void): void {
    if (!get(modelSaveAsAliases))
      return;
    const failures = Object.entries(get(modelMappings))
      .filter(([alias, location]) => alias.trim() !== '' && location !== '')
      .map(async ([alias, location]) => saveAlias(alias, location)
        .then(outcome => (outcome.ok ? undefined : `${alias.trim()}: ${outcome.error}`)));
    startPromise(Promise.all(failures).then((reasons) => {
      const failed = reasons.filter(reason => reason !== undefined);
      if (failed.length > 0)
        onFailure(failed.join('; '));
    }));
  }

  function reset(): void {
    generation += 1;
    set(resolutions, []);
    set(modelMappings, {});
  }

  return {
    checkLocations,
    choicesMissing,
    modelMappings,
    modelSaveAsAliases,
    pending,
    rememberAliases,
    reset,
  };
}
