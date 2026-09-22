import type { EffectScope } from 'vue';
import type { ActionItem, ActionItemOption } from '@/modules/core/action-center/types';
import { mockUseSupportedChains } from '@test/utils/mocks/supported-chains';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { getServiceRegisterUrl } from '@/modules/core/common/helpers/url';
import { INDEXER_SETTINGS } from '@/modules/shell/action-center/row-options';
import { useChainRows } from '@/modules/shell/action-center/use-chain-rows';
import { RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const suppressedChains = ref<string[]>([]);
const updateFrontendSetting = vi.fn<(payload: object) => Promise<{ success: boolean }>>();
const show = vi.fn<(message: { title: string; message: string }, onConfirm: () => Promise<void>) => void>();

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<string[]> => suppressedChains,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () =>
  mockUseSupportedChains({ getChainName: (chain: string): string => chain.toUpperCase() }));

let scope: EffectScope | undefined;

function rows(): ComputedRef<ActionItem[]> {
  scope = effectScope();
  const result = scope.run(() => useChainRows());
  assert(result);
  return result;
}

function raiseNoIndexers(chain: string, paidKeyRequired = false): void {
  useRaisedConditionsStore().raise({ chain, kind: RaisedConditionKind.NO_AVAILABLE_INDEXERS, paidKeyRequired });
}

function option(row: ActionItem, id: string): ActionItemOption {
  const found = row.options.find(candidate => candidate.id === id);
  assert(found);
  return found;
}

describe('modules/shell/action-center/use-chain-rows', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    updateFrontendSetting.mockResolvedValue({ success: true });
    set(suppressedChains, []);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should raise a row per chain no indexer could serve, pointing at the indexer settings', () => {
    raiseNoIndexers('optimism');
    raiseNoIndexers('binance_sc');

    const [optimism, binance] = get(rows());

    expect(optimism.id).toBe('no-available-indexers-optimism');
    expect(binance.id).toBe('no-available-indexers-binance-sc');
    expect(optimism.target).toEqual(INDEXER_SETTINGS);
    expect(optimism.title).toBe('action_center.rows.chains.no_indexers.title::OPTIMISM');
  });

  it('should point a row that needs a paid key at the Etherscan key instead', () => {
    raiseNoIndexers('base', true);

    const [base] = get(rows());

    expect(base.target).toEqual({ kind: 'route', to: getServiceRegisterUrl('etherscan')?.route });
    expect(base.title).toBe('action_center.rows.chains.paid_key_required.title::BASE');
  });

  it('should keep configuring the indexers as an option on a paid-key row, and not repeat it on a plain one', () => {
    raiseNoIndexers('base', true);
    raiseNoIndexers('optimism');

    const [base, optimism] = get(rows());

    expect(base.options.map(({ id }) => id)).toEqual(['configure-indexers', 'do-not-show-again']);
    expect(option(base, 'configure-indexers').target).toEqual(INDEXER_SETTINGS);
    expect(optimism.options.map(({ id }) => id)).toEqual(['do-not-show-again']);
  });

  it('should ask before suppressing a chain, then add it to the suppressed chains', async () => {
    set(suppressedChains, ['gnosis']);
    raiseNoIndexers('optimism');

    const suppress = option(get(rows())[0], 'do-not-show-again');
    expect(suppress.danger).toBe(true);
    assert(suppress.target.kind === 'run');
    suppress.target.run();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
    const [message, onConfirm] = show.mock.calls[0];
    expect(message.title).toBe('action_center.rows.chains.suppress_confirm.title::OPTIMISM');

    await onConfirm();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ suppressNoIndexerChains: ['gnosis', 'optimism'] });
  });

  it('should leave out a chain the user suppressed, even one raised before', () => {
    raiseNoIndexers('optimism');
    const result = rows();

    set(suppressedChains, ['optimism']);

    expect(get(result)).toEqual([]);
  });

  it('should leave conditions of other modules to their own rows', () => {
    useRaisedConditionsStore().raise({ kind: RaisedConditionKind.MONERIUM_SESSION });

    expect(get(rows())).toEqual([]);
  });
});
