import type { MissingMapping } from '@/modules/user-data/schemas';
import { useMissingMappingsDB } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-db';
import { useAssetCexMappingApi } from '@/modules/assets/api/use-asset-cex-mapping-api';
import { logger } from '@/modules/core/common/logging/logging';
import { captureSession } from '@/modules/core/session/session-lifecycle';

interface UsePruneResolvedMappingsReturn {
  /**
   * Deletes the recorded mappings the backend now resolves.
   *
   * @returns how many were deleted; zero when nothing resolved or the check failed
   */
  prune: () => Promise<number>;
}

function keyOf(location: string | null, symbol: string): string {
  return JSON.stringify([location, symbol]);
}

/**
 * Drops recorded unknown exchange assets that have since become resolvable.
 *
 * @remarks
 * A record is a past report, and nothing reports that it stopped being true: a data update, an
 * assets update or a mapping added anywhere can resolve the symbol later. The backend is asked
 * about every record with the rules the exchange's own queries use, so the cause does not matter.
 */
export function usePruneResolvedMappings(): UsePruneResolvedMappingsReturn {
  const { getAll, removeByIds } = useMissingMappingsDB();
  const { resolveCexSymbols } = useAssetCexMappingApi();

  async function prune(): Promise<number> {
    const sameSession = captureSession();
    try {
      const records = (await getAll()).filter(({ identifier, location }: MissingMapping) => identifier && location);
      if (records.length === 0)
        return 0;

      const resolved = new Set((await resolveCexSymbols(
        records.map(({ identifier, location }) => ({ location, locationSymbol: identifier })),
      )).map(({ location, locationSymbol }) => keyOf(location, locationSymbol)));

      const ids = records.filter(({ identifier, location }) => resolved.has(keyOf(location, identifier))).map(({ id }) => id);
      if (ids.length === 0 || !sameSession())
        return 0;

      await removeByIds(ids);
      return ids.length;
    }
    catch (error: unknown) {
      logger.error(error);
      return 0;
    }
  }

  return { prune };
}
