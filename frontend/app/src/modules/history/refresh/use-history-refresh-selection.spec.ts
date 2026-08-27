import { beforeEach, describe, expect, it } from 'vitest';
import { nextTick } from 'vue';
import { OnlineHistoryEventsQueryType } from '@/modules/history/events/schemas';
import { type HistoryRefreshTab, useHistoryRefreshSelection } from '@/modules/history/refresh/use-history-refresh-selection';

const MOCK_T_PLURAL_SUFFIX = '::';

describe('useHistoryRefreshSelection', () => {
  let selection: ReturnType<typeof useHistoryRefreshSelection>;

  beforeEach(() => {
    selection = useHistoryRefreshSelection();
  });

  async function switchTo(tab: HistoryRefreshTab): Promise<void> {
    set(selection.modelTab, tab);
    await nextTick();
  }

  it('should start on the chains tab with nothing picked', () => {
    const { indeterminate, modelTab, selected, totalSelected } = selection;

    expect(get(modelTab)).toBe('chains');
    expect(get(totalSelected)).toBe(0);
    expect(get(indeterminate)).toBe(false);
    expect(get(selected)).toBe(false);
  });

  it('should count only the active tab', async () => {
    const { modelSelectedAccounts, modelSelectedExchanges, totalSelected } = selection;

    set(modelSelectedAccounts, [{ address: '0x1', chain: 'eth' }, { address: '0x2', chain: 'eth' }]);
    expect(get(totalSelected)).toBe(2);

    await switchTo('exchanges');
    set(modelSelectedExchanges, [{ location: 'kraken', name: 'Kraken 1' }]);
    expect(get(totalSelected)).toBe(1);
  });

  it('should be indeterminate for a partial pick and selected once the tab reports all', () => {
    const { indeterminate, modelSelectedAccounts, selected, setAllSelected } = selection;

    set(modelSelectedAccounts, [{ address: '0x1', chain: 'eth' }]);
    expect(get(indeterminate)).toBe(true);
    expect(get(selected)).toBe(false);

    setAllSelected('chains', true);
    expect(get(indeterminate)).toBe(false);
    expect(get(selected)).toBe(true);
  });

  it('should stay unselected when a tab reports all with nothing picked', () => {
    const { indeterminate, selected, setAllSelected } = selection;

    setAllSelected('chains', true);

    expect(get(indeterminate)).toBe(false);
    expect(get(selected)).toBe(false);
  });

  it('should read the select-all state from the active tab', async () => {
    const { modelSelectedExchanges, selected, setAllSelected } = selection;

    await switchTo('exchanges');
    set(modelSelectedExchanges, [{ location: 'kraken', name: 'Kraken 1' }]);
    setAllSelected('exchanges', true);
    expect(get(selected)).toBe(true);

    await switchTo('protocols');
    expect(get(selected)).toBe(false);
  });

  it('should drop every pick and the all-selected flag when the tab changes', async () => {
    const { modelSearch, modelSelectedAccounts, modelSelectedChain, selected, setAllSelected } = selection;

    set(modelSearch, 'eth');
    set(modelSelectedChain, 'eth');
    set(modelSelectedAccounts, [{ address: '0x1', chain: 'eth' }]);
    setAllSelected('chains', true);

    await switchTo('events');

    expect(get(modelSearch)).toBe('');
    expect(get(modelSelectedChain)).toBeUndefined();
    expect(get(modelSelectedAccounts)).toEqual([]);

    await switchTo('chains');
    expect(get(selected)).toBe(false);
  });

  it('should clear every tab on reset', async () => {
    const {
      modelSelectedExchanges,
      modelSelectedProtocolQueries,
      modelSelectedQueries,
      reset,
      selected,
      setAllSelected,
    } = selection;

    await switchTo('protocols');
    set(modelSelectedExchanges, [{ location: 'kraken', name: 'Kraken 1' }]);
    set(modelSelectedQueries, [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS]);
    set(modelSelectedProtocolQueries, [OnlineHistoryEventsQueryType.GNOSIS_PAY]);
    setAllSelected('protocols', true);

    reset();

    expect(get(modelSelectedExchanges)).toEqual([]);
    expect(get(modelSelectedQueries)).toEqual([]);
    expect(get(modelSelectedProtocolQueries)).toEqual([]);
    expect(get(selected)).toBe(false);
  });

  describe('searchLabel', () => {
    it('should ask for a chain until one is picked, then for an address', () => {
      const { modelSelectedChain, searchLabel } = selection;

      expect(get(searchLabel)).toBe('history_refresh_selection.search_chain');

      set(modelSelectedChain, 'eth');
      expect(get(searchLabel)).toBe('history_refresh_selection.search_address');
    });

    it.each<[HistoryRefreshTab, string]>([
      ['exchanges', 'history_refresh_selection.search_exchanges'],
      ['events', 'history_refresh_selection.search_events'],
      ['protocols', 'history_refresh_selection.search_protocols'],
    ])('should label the search for the %s tab', async (tab, expected) => {
      await switchTo(tab);
      expect(get(selection.searchLabel)).toBe(expected);
    });
  });

  describe('typeText', () => {
    it.each<[HistoryRefreshTab, string]>([
      ['chains', 'history_refresh_selection.type.accounts'],
      ['exchanges', 'history_refresh_selection.type.exchanges'],
      ['events', 'history_refresh_selection.type.events'],
      ['protocols', 'history_refresh_selection.type.protocols'],
    ])('should name what the %s tab refreshes', async (tab, expected) => {
      await switchTo(tab);
      expect(get(selection.typeText)).toBe(expected);
    });

    it('should pluralize by how many are picked', () => {
      const { modelSelectedAccounts, typeText } = selection;

      set(modelSelectedAccounts, [{ address: '0x1', chain: 'eth' }, { address: '0x2', chain: 'eth' }]);

      expect(get(typeText)).toBe(`history_refresh_selection.type.accounts${MOCK_T_PLURAL_SUFFIX}`);
    });
  });

  describe('getRefreshPayload', () => {
    it('should send the picked accounts from the chains tab', () => {
      const accounts = [{ address: '0x1', chain: 'eth' }];
      set(selection.modelSelectedAccounts, accounts);

      expect(selection.getRefreshPayload()).toEqual({ accounts });
    });

    it('should send the picked exchanges from the exchanges tab', async () => {
      const exchanges = [{ location: 'kraken', name: 'Kraken 1' }];
      await switchTo('exchanges');
      set(selection.modelSelectedExchanges, exchanges);

      expect(selection.getRefreshPayload()).toEqual({ exchanges });
    });

    it('should send the staking queries from the events tab', async () => {
      const queries = [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS];
      await switchTo('events');
      set(selection.modelSelectedQueries, queries);

      expect(selection.getRefreshPayload()).toEqual({ queries });
    });

    it('should send the protocol queries from the protocols tab', async () => {
      const queries = [OnlineHistoryEventsQueryType.GNOSIS_PAY];
      await switchTo('protocols');
      set(selection.modelSelectedProtocolQueries, queries);

      expect(selection.getRefreshPayload()).toEqual({ queries });
    });
  });
});
