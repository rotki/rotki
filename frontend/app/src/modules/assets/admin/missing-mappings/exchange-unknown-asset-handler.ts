import type { MessageHandler } from '@/modules/core/messaging/interfaces';
import type { ExchangeUnknownAssetData } from '@/modules/core/messaging/types/business-types';
import { pick } from 'es-toolkit';
import { useMissingMappingsCount } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-count';
import { useMissingMappingsDB } from '@/modules/assets/admin/missing-mappings/use-missing-mappings-db';
import { createConditionalHandler } from '@/modules/core/messaging/utils';

/**
 * Records an exchange asset rotki could not map, which the action center counts from the table.
 *
 * @remarks
 * Creates no notification. The backend repeats the report on every query cycle, and the table's
 * unique index rejects a repeat, which the conditional handler absorbs.
 */
export function createExchangeUnknownAssetHandler(): MessageHandler<ExchangeUnknownAssetData> {
  const { put } = useMissingMappingsDB();
  const { refresh } = useMissingMappingsCount();

  return createConditionalHandler<ExchangeUnknownAssetData>(async (data) => {
    await put(pick(data, ['identifier', 'location', 'name', 'details']));
    await refresh();
    return null;
  });
}
