import type { Eth2ValidatorEntry, EthStakingCombinedFilter, EthStakingFilter } from '@rotki/common';
import type { Ref } from 'vue';
import type { MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { describe, expect, it } from 'vitest';
import { useEthStakingSelection } from './use-eth-staking-selection';
import '@test/i18n';

const VALIDATOR: Eth2ValidatorEntry = {
  index: 42,
  publicKey: '0xabc',
  status: 'active',
};

const OTHER_VALIDATOR: Eth2ValidatorEntry = {
  index: 7,
  publicKey: '0xdef',
  status: 'active',
};

const ADDRESS = '0x5A0b54D5dc17e0AadC383d2db43B0a0D3E029c4c';

interface Harness {
  matches: Ref<MatchedKeywordWithBehaviour<string>>;
  selection: Ref<EthStakingFilter>;
  filter: Ref<EthStakingCombinedFilter | undefined>;
  unmount: () => void;
}

function createHarness(initial: EthStakingFilter = { validators: [] }): Harness {
  setActivePinia(createCustomPinia());
  const selection = ref<EthStakingFilter>(initial);
  const filter = ref<EthStakingCombinedFilter>();
  const { result, wrapper } = withSetup(() => useEthStakingSelection(selection, filter));

  return { filter, matches: get(result).modelMatches, selection, unmount: () => wrapper.unmount() };
}

describe('useEthStakingSelection', () => {
  it('should read a validator selection as its indices', () => {
    const { matches, unmount } = createHarness({ validators: [VALIDATOR, OTHER_VALIDATOR] });

    expect(get(matches)).toStrictEqual({ validator: ['42', '7'] });

    unmount();
  });

  it('should read an address selection as its addresses', () => {
    const { matches, unmount } = createHarness({ accounts: [{ address: ADDRESS, chain: 'eth' }] });

    expect(get(matches)).toStrictEqual({ withdrawalAddress: [ADDRESS] });

    unmount();
  });

  // `{ key: undefined }` is not `{}` to the bar's round-trip guard: a bag carrying undefined keys
  // makes a pill vanish the moment it is added.
  it('should omit a key entirely rather than carry it as undefined', () => {
    const { matches, unmount } = createHarness();

    expect(get(matches)).toStrictEqual({});
    expect(Object.keys(get(matches))).toHaveLength(0);

    unmount();
  });

  it('should write picked indices back as whole validator entries', () => {
    const { matches, selection, unmount } = createHarness({ validators: [VALIDATOR, OTHER_VALIDATOR] });

    set(matches, { validator: ['7'] });

    // The premium component declares the whole entry, even though it reads only the index.
    expect(get(selection)).toStrictEqual({ validators: [OTHER_VALIDATOR] });

    unmount();
  });

  it('should write picked addresses back as accounts on ethereum', () => {
    const { matches, selection, unmount } = createHarness();

    set(matches, { withdrawalAddress: [ADDRESS] });

    expect(get(selection)).toStrictEqual({ accounts: [{ address: ADDRESS, chain: 'eth' }] });

    unmount();
  });

  // The union has no empty member, and the component branches on `'accounts' in filter`, so the
  // cleared state has to be a shape rather than undefined.
  it('should fall back to an empty validator selection when every pill is cleared', () => {
    const { matches, selection, unmount } = createHarness({ accounts: [{ address: ADDRESS, chain: 'eth' }] });

    set(matches, {});

    expect(get(selection)).toStrictEqual({ validators: [] });

    unmount();
  });

  // The pill carries an index, the model wants the entry, and the store loads asynchronously.
  // Resolving straight from an empty store would silently empty the selection.
  it('should keep a validator the store has not loaded', () => {
    const { matches, selection, unmount } = createHarness({ validators: [VALIDATOR] });

    // The pinia here is empty, so the validators store resolves nothing at all.
    set(matches, { validator: ['42'] });

    expect(get(selection)).toStrictEqual({ validators: [VALIDATOR] });

    unmount();
  });

  it('should round-trip a full bag through both directions unchanged', () => {
    const { matches, unmount } = createHarness({ validators: [VALIDATOR] });
    const bag = { fromTimestamp: '1600000000', status: 'active', toTimestamp: '1700000000', validator: ['42'] };

    set(matches, bag);

    expect(get(matches)).toStrictEqual(bag);

    unmount();
  });

  it('should carry the period and status onto the combined filter', () => {
    const { filter, matches, unmount } = createHarness();

    set(matches, { fromTimestamp: '1600000000', status: 'exited', toTimestamp: '1700000000' });

    expect(get(filter)).toStrictEqual({
      fromTimestamp: 1600000000,
      status: 'exited',
      toTimestamp: 1700000000,
    });

    unmount();
  });
});
