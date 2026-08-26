import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { createAssetMovementEvent, createEvmEvent } from '@test/utils/history-events';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  getMovementDestinationAddress,
  useUntrackedMovementDestination,
} from '@/modules/history/events/use-untracked-movement-destination';

/**
 * The seam: which movements may be called unmatchable because their counterpart is not
 * tracked. Only a withdrawal qualifies -- a deposit's recorded address is usually the
 * exchange's own deposit address, so answering for one would flag nearly every deposit.
 */

const trackedAddressesRef = ref<Record<string, string[]>>({});
const accountsReadyRef = ref<boolean>(true);

vi.mock('@/modules/balances/blockchain/use-account-addresses', () => ({
  useAccountAddresses: (): object => ({
    addresses: computed<Record<string, string[]>>(() => get(trackedAddressesRef)),
  }),
}));

vi.mock('@/modules/accounts/use-account-load-state', () => ({
  useAccountLoadState: (): object => ({
    ready: computed<boolean>(() => get(accountsReadyRef)),
  }),
}));

/**
 * Creates an asset movement as the exchange reported it.
 *
 * @param overrides - omitting `address` means the exchange recorded none, which is not the same as
 * recording an untracked one
 */
function createEntry(overrides: { eventSubtype?: string; address?: string | null } = {}): HistoryEventEntry {
  return createAssetMovementEvent({
    eventSubtype: overrides.eventSubtype ?? 'spend',
    extraData: overrides.address === undefined ? null : { address: overrides.address },
  });
}

describe('use-untracked-movement-destination', () => {
  beforeEach(() => {
    set(trackedAddressesRef, { eth: ['0xTracked'] });
    set(accountsReadyRef, true);
  });

  describe('getMovementDestinationAddress', () => {
    it('should return the recorded address of a withdrawal', () => {
      expect(getMovementDestinationAddress(createEntry({ address: '0xdef' }))).toBe('0xdef');
    });

    it('should return nothing for a deposit, whose address is the exchange side', () => {
      expect(getMovementDestinationAddress(createEntry({ address: '0xdef', eventSubtype: 'receive' }))).toBeUndefined();
    });

    it('should return nothing when the exchange recorded no address', () => {
      expect(getMovementDestinationAddress(createEntry())).toBeUndefined();
    });

    it('should return nothing for an event that is not an asset movement', () => {
      expect(getMovementDestinationAddress(createEvmEvent({ extraData: { address: '0xdef' } }))).toBeUndefined();
    });
  });

  describe('isDestinationUntracked', () => {
    it('should be true for a withdrawal to an address rotki does not track', () => {
      const { isDestinationUntracked } = useUntrackedMovementDestination();

      expect(isDestinationUntracked(createEntry({ address: '0xUntracked' }))).toBe(true);
    });

    it('should be false for a withdrawal to a tracked address, ignoring case', () => {
      const { isDestinationUntracked } = useUntrackedMovementDestination();

      expect(isDestinationUntracked(createEntry({ address: '0xTRACKED' }))).toBe(false);
    });

    it('should be false without a recorded address, since nothing is known', () => {
      const { isDestinationUntracked } = useUntrackedMovementDestination();

      expect(isDestinationUntracked(createEntry())).toBe(false);
    });

    it('should be false before the accounts have been read, however untracked the address looks', () => {
      set(trackedAddressesRef, {});
      set(accountsReadyRef, false);
      const { isDestinationUntracked } = useUntrackedMovementDestination();

      expect(isDestinationUntracked(createEntry({ address: '0xUntracked' }))).toBe(false);
    });

    it('should count an address tracked on any chain as tracked', () => {
      set(trackedAddressesRef, { optimism: ['0xElsewhere'] });
      const { isDestinationUntracked } = useUntrackedMovementDestination();

      expect(isDestinationUntracked(createEntry({ address: '0xElsewhere' }))).toBe(false);
    });
  });
});
