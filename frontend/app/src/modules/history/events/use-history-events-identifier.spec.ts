import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { createAssetMovementEvent, createEthBlockEvent, createEvmEvent, createOnlineHistoryEvent, createWithdrawalEvent } from '@test/utils/history-events';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { effectScope } from 'vue';
import { useHistoryEventsIdentifier } from './use-history-events-identifier';

const { is2xlAndUp, isMd } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return { is2xlAndUp: ref<boolean>(false), isMd: ref<boolean>(false) };
});

vi.mock('@rotki/ui-library', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@rotki/ui-library')>();
  return {
    ...actual,
    useBreakpoint: (): Record<string, unknown> => ({ is2xlAndUp, isMd }),
  };
});

let scope: ReturnType<typeof effectScope>;

function identifier(
  current: HistoryEventEntry,
  groupEvents?: HistoryEventEntry[],
): ReturnType<typeof useHistoryEventsIdentifier> {
  scope = effectScope();
  return scope.run(() => useHistoryEventsIdentifier(() => current, () => groupEvents))!;
}

describe('modules/history/events/useHistoryEventsIdentifier', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(is2xlAndUp, false);
    set(isMd, false);
  });

  afterEach(() => {
    scope?.stop();
  });

  describe('the header message', () => {
    it('should use the type\'s own header when the event carries no transaction reference', () => {
      const { translationKey } = identifier(createOnlineHistoryEvent());

      expect(get(translationKey)).toBe('transactions.events.headers.history_event');
    });

    it('should use the evm header for an event carrying a transaction reference', () => {
      const { translationKey } = identifier(createEvmEvent({ txRef: '0xdead' }));

      expect(get(translationKey)).toBe('transactions.events.headers.evm_event');
    });

    it('should keep an asset movement on its own header despite carrying a reference', () => {
      const movement = { ...createAssetMovementEvent(), txRef: '0xdead' };

      const { translationKey } = identifier(movement);

      expect(get(translationKey)).toBe('transactions.events.headers.asset_movement_event');
    });
  });

  describe('the render key', () => {
    it('should prefer the transaction reference over every other shape', () => {
      const movement = { ...createAssetMovementEvent(), txRef: '0xdead' };

      expect(get(identifier(movement).key)).toBe('tx_hash');
    });

    it('should report an asset movement carrying no reference as such', () => {
      expect(get(identifier(createAssetMovementEvent()).key)).toBe('asset_movement');
    });

    it('should report a block production event as a block', () => {
      expect(get(identifier(createEthBlockEvent()).key)).toBe('block');
    });

    it('should report a validator withdrawal as a withdrawal', () => {
      expect(get(identifier(createWithdrawalEvent()).key)).toBe('withdraw');
    });

    it('should report a plain event as having no identifier shape', () => {
      expect(get(identifier(createOnlineHistoryEvent()).key)).toBeUndefined();
    });
  });

  describe('the transaction references of a group', () => {
    it('should be empty for an event that is not an asset movement', () => {
      const { allTxRefs } = identifier(createEvmEvent({ txRef: '0xdead' }), [createEvmEvent({ txRef: '0xbeef' })]);

      expect(get(allTxRefs)).toEqual([]);
    });

    it('should be empty when no group was given', () => {
      const { allTxRefs } = identifier(createAssetMovementEvent());

      expect(get(allTxRefs)).toEqual([]);
    });

    it('should collect one entry per distinct reference, in group order', () => {
      const { allTxRefs } = identifier(createAssetMovementEvent(), [
        createEvmEvent({ location: 'ethereum', txRef: '0xaaa' }),
        createEvmEvent({ location: 'optimism', txRef: '0xbbb' }),
      ]);

      expect(get(allTxRefs)).toEqual([
        { location: 'ethereum', txRef: '0xaaa' },
        { location: 'optimism', txRef: '0xbbb' },
      ]);
    });

    it('should keep only the first sighting of a repeated reference', () => {
      const { allTxRefs } = identifier(createAssetMovementEvent(), [
        createEvmEvent({ location: 'ethereum', txRef: '0xaaa' }),
        createEvmEvent({ location: 'optimism', txRef: '0xaaa' }),
      ]);

      expect(get(allTxRefs)).toEqual([{ location: 'ethereum', txRef: '0xaaa' }]);
    });

    it('should skip group members carrying no reference', () => {
      const { allTxRefs } = identifier(createAssetMovementEvent(), [
        createOnlineHistoryEvent(),
        createEvmEvent({ txRef: '0xaaa' }),
      ]);

      expect(get(allTxRefs)).toHaveLength(1);
    });
  });

  describe('the extra reference count', () => {
    it('should count everything beyond the one already shown', () => {
      const { extraHashCount } = identifier(createAssetMovementEvent(), [
        createEvmEvent({ txRef: '0xaaa' }),
        createEvmEvent({ txRef: '0xbbb' }),
        createEvmEvent({ txRef: '0xccc' }),
      ]);

      expect(get(extraHashCount)).toBe(2);
    });

    it('should never go negative when there is nothing to show', () => {
      expect(get(identifier(createOnlineHistoryEvent()).extraHashCount)).toBe(0);
    });
  });

  describe('the movement transaction id', () => {
    it('should read it from the movement extra data', () => {
      const movement = createAssetMovementEvent({ extraData: { transactionId: 'abc123' } });

      expect(get(identifier(movement).assetMovementTransactionId)).toBe('abc123');
    });

    it('should be undefined when the movement carries no extra data', () => {
      expect(get(identifier(createAssetMovementEvent()).assetMovementTransactionId)).toBeUndefined();
    });

    it('should be undefined for an event that is not a movement at all', () => {
      expect(get(identifier(createOnlineHistoryEvent()).assetMovementTransactionId)).toBeUndefined();
    });
  });

  describe('the truncation width', () => {
    it('should show most of a hash on the widest viewport', () => {
      set(is2xlAndUp, true);

      expect(get(identifier(createOnlineHistoryEvent()).truncateLength)).toBe(12);
    });

    it('should show least at the medium breakpoint, where the column is tightest', () => {
      set(isMd, true);

      expect(get(identifier(createOnlineHistoryEvent()).truncateLength)).toBe(6);
    });

    it('should sit between the two elsewhere', () => {
      expect(get(identifier(createOnlineHistoryEvent()).truncateLength)).toBe(8);
    });
  });
});
