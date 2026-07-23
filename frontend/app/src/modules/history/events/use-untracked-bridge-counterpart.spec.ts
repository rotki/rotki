import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getBridgeCounterpartAddress,
  useBridgeUnmatchableExplanation,
  useUntrackedBridgeCounterpart,
} from '@/modules/history/events/use-untracked-bridge-counterpart';

const trackedAddressesRef = ref<Record<string, string[]>>({});

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: (): object => ({
    addresses: computed<Record<string, string[]>>(() => get(trackedAddressesRef)),
  }),
}));

function createTransaction(overrides: {
  direction?: 'deposit' | 'withdrawal';
  bridge?: UnmatchedBridgeTransaction['bridge'];
} = {}): UnmatchedBridgeTransaction {
  return {
    groupIdentifier: 'group1',
    // @ts-expect-error partial mock for testing - the events are not read by these helpers
    events: { entry: { identifier: 1 } },
    identifier: 1,
    asset: 'ETH',
    bridge: overrides.bridge,
    direction: overrides.direction ?? 'deposit',
  };
}

describe('use-untracked-bridge-counterpart', () => {
  beforeEach(() => {
    set(trackedAddressesRef, {
      eth: ['0xTracked'],
      optimism: ['0xL2Tracked'],
    });
  });

  describe('getBridgeCounterpartAddress', () => {
    it('should return the destination address for a deposit', () => {
      const transaction = createTransaction({ bridge: { fromAddress: '0xabc', toAddress: '0xdef' } });
      expect(getBridgeCounterpartAddress(transaction)).toBe('0xdef');
    });

    it('should return the source address for a withdrawal', () => {
      const transaction = createTransaction({
        bridge: { fromAddress: '0xabc', toAddress: '0xdef' },
        direction: 'withdrawal',
      });
      expect(getBridgeCounterpartAddress(transaction)).toBe('0xabc');
    });

    it('should return undefined without recorded bridge data', () => {
      expect(getBridgeCounterpartAddress(createTransaction())).toBeUndefined();
    });
  });

  describe('isCounterpartUntracked', () => {
    it('should report an unknown destination address as untracked', () => {
      const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();
      expect(isCounterpartUntracked(createTransaction({ bridge: { toAddress: '0xdef' } }))).toBe(true);
    });

    it('should treat an address tracked on any chain as tracked, ignoring case', () => {
      const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();
      expect(isCounterpartUntracked(createTransaction({ bridge: { toAddress: '0xl2tracked' } }))).toBe(false);
    });

    it('should not flag a leg without a recorded counterpart address', () => {
      const { isCounterpartUntracked } = useUntrackedBridgeCounterpart();
      expect(isCounterpartUntracked(createTransaction())).toBe(false);
    });
  });

  describe('useBridgeUnmatchableExplanation', () => {
    it('should explain an unmatchable deposit via its untracked destination', () => {
      const { unmatchableExplanation } = useBridgeUnmatchableExplanation(createTransaction({ bridge: { toAddress: '0xdef' } }));
      expect(get(unmatchableExplanation)).toBe('bridge_matching.dialog.no_match_untracked_destination::0xdef');
    });

    it('should explain an unmatchable withdrawal via its untracked source', () => {
      const transaction = createTransaction({ bridge: { fromAddress: '0xabc' }, direction: 'withdrawal' });
      const { unmatchableExplanation } = useBridgeUnmatchableExplanation(transaction);
      expect(get(unmatchableExplanation)).toBe('bridge_matching.dialog.no_match_untracked_source::0xabc');
    });

    it('should return undefined when the counterpart address is tracked', () => {
      const transaction = createTransaction({ bridge: { toAddress: '0xTracked' } });
      const { unmatchableExplanation } = useBridgeUnmatchableExplanation(transaction);
      expect(get(unmatchableExplanation)).toBeUndefined();
    });

    it('should return undefined when no transaction is selected', () => {
      const { unmatchableExplanation } = useBridgeUnmatchableExplanation(undefined);
      expect(get(unmatchableExplanation)).toBeUndefined();
    });
  });
});
