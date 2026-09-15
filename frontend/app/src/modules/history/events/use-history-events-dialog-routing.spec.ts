import type { EffectScope } from 'vue';
import type { LocationQuery } from 'vue-router';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';
import { useHistoryEventsDialogRouting } from '@/modules/history/events/use-history-events-dialog-routing';

const route = reactive<{ query: LocationQuery }>({ query: {} });
const replace = vi.fn<(to: unknown) => Promise<void>>();

vi.mock('vue-router', () => ({
  useRoute: (): object => route,
  useRouter: (): object => ({ replace }),
}));

let scope: EffectScope | undefined;

function setup(): ReturnType<typeof vi.fn<(options: DialogShowOptions) => void>> {
  const show = vi.fn<(options: DialogShowOptions) => void>();
  const container = shallowRef<{ show: typeof show } | null>({ show });
  scope = effectScope();
  scope.run(() => useHistoryEventsDialogRouting(container));
  return show;
}

describe('modules/history/events/use-history-events-dialog-routing', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    route.query = {};
    replace.mockResolvedValue();
  });

  afterEach(() => {
    scope?.stop();
    scope = undefined;
  });

  it.each([
    ['openCustomizedEventDuplicatesDialog', DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES],
    ['openDecodingStatusDialog', DIALOG_TYPES.DECODING_STATUS],
    ['openInternalTxConflictsDialog', DIALOG_TYPES.INTERNAL_TX_CONFLICTS],
    ['openMatchAssetMovementsDialog', DIALOG_TYPES.MATCH_ASSET_MOVEMENTS],
    ['openMatchBridgesDialog', DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS],
  ])('should open the dialog %s asks for and drop the key', async (key, type) => {
    route.query = { [key]: 'true' };

    const show = setup();
    await flushPromises();

    expect(show).toHaveBeenCalledExactlyOnceWith({ type });
    expect(replace).toHaveBeenCalledExactlyOnceWith({ query: {} });
  });

  it('should leave the page alone when the query names no dialog', async () => {
    route.query = { groupIdentifiers: 'a,b' };

    const show = setup();
    await flushPromises();

    expect(show).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
  });
});
