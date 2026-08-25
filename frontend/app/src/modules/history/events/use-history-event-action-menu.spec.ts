import type { EthBlockEvent, EvmHistoryEvent, HistoryEventEntry } from '@/modules/history/events/schemas';
import { HistoryEventEntryType } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import {
  useHistoryEventActionMenu,
  type UseHistoryEventActionMenuReturn,
} from '@/modules/history/events/use-history-event-action-menu';

const ethBlockEventsDecoding = ref<boolean>(false);
const txEventsDecoding = ref<boolean>(false);

vi.mock('@/modules/history/events/use-history-events-status', () => ({
  useHistoryEventsStatus: (): Record<string, unknown> => ({ ethBlockEventsDecoding, txEventsDecoding }),
}));

const confirmAndFixDuplicate = vi.fn();
const confirmAndMarkNonDuplicated = vi.fn();
const fixLoading = ref<boolean>(false);
const ignoreLoading = ref<boolean>(false);

vi.mock('@/modules/history/events/use-customized-event-duplicates', () => ({
  useCustomizedEventDuplicates: (): Record<string, unknown> => ({
    confirmAndFixDuplicate,
    confirmAndMarkNonDuplicated,
    fixLoading,
    ignoreLoading,
  }),
}));

const showReportIssue = vi.fn();

vi.mock('@/modules/core/common/use-report-issue', () => ({
  useReportIssue: (): Record<string, unknown> => ({ show: showReportIssue }),
}));

function createEvent(overrides: Partial<HistoryEventEntry>): HistoryEventEntry {
  return createMock<HistoryEventEntry>({ identifier: 1, location: 'ethereum', ...overrides });
}

const evmEvent = createEvent({
  entryType: HistoryEventEntryType.EVM_EVENT,
  groupIdentifier: 'group-a',
  txRef: '0xabc',
});

const solanaEvent = createEvent({
  entryType: HistoryEventEntryType.SOLANA_EVENT,
  location: 'solana',
  txRef: 'sol-sig',
});

const blockEvent = createEvent({
  blockNumber: 1234,
  entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
});

/** The same two events, typed as what a re-decode payload is built from. */
const decodableEvm = createMock<EvmHistoryEvent>({
  entryType: HistoryEventEntryType.EVM_EVENT,
  location: 'ethereum',
  txRef: '0xabc',
});

const decodableBlock = createMock<EthBlockEvent>({
  blockNumber: 1234,
  entryType: HistoryEventEntryType.ETH_BLOCK_EVENT,
});

const onlineEvent = createEvent({
  entryType: HistoryEventEntryType.HISTORY_EVENT,
  location: 'kraken',
});

const event = ref<HistoryEventEntry>(evmEvent);
const groupEvents = ref<HistoryEventEntry[] | undefined>();
const duplicateHandlingStatus = ref<DuplicateHandlingStatus | undefined>();
const onFixDuplicate = vi.fn();
const onIgnoreDuplicate = vi.fn();

interface Harness {
  wrapper: VueWrapper;
  menu: UseHistoryEventActionMenuReturn;
}

function mountMenu(): Harness {
  let menu!: UseHistoryEventActionMenuReturn;
  const Comp = defineComponent({
    setup(): () => null {
      menu = useHistoryEventActionMenu({
        duplicateHandlingStatus: () => get(duplicateHandlingStatus),
        event: () => get(event),
        groupEvents: () => get(groupEvents),
        onFixDuplicate,
        onIgnoreDuplicate,
      });
      return (): null => null;
    },
  });
  const wrapper = mount(Comp);
  return { menu, wrapper };
}

describe('useHistoryEventActionMenu', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(event, evmEvent);
    set(groupEvents, undefined);
    set(duplicateHandlingStatus, undefined);
    set(ethBlockEventsDecoding, false);
    set(txEventsDecoding, false);
  });

  describe('the duplicate actions', () => {
    it('should offer neither action for a row that is not a duplicate', () => {
      const { menu } = mountMenu();

      expect(get(menu.isAutoFixable)).toBe(false);
      expect(get(menu.isDuplicate)).toBe(false);
    });

    it('should offer both actions for an auto-fixable duplicate', () => {
      set(duplicateHandlingStatus, DuplicateHandlingStatus.AUTO_FIX);
      const { menu } = mountMenu();

      expect(get(menu.isAutoFixable)).toBe(true);
      expect(get(menu.isDuplicate)).toBe(true);
    });

    it('should offer only the dismissal for a duplicate needing review', () => {
      set(duplicateHandlingStatus, DuplicateHandlingStatus.MANUAL_REVIEW);
      const { menu } = mountMenu();

      expect(get(menu.isAutoFixable)).toBe(false);
      expect(get(menu.isDuplicate)).toBe(true);
    });

    it('should offer neither action for a duplicate already dismissed', () => {
      set(duplicateHandlingStatus, DuplicateHandlingStatus.IGNORED);
      const { menu } = mountMenu();

      expect(get(menu.isAutoFixable)).toBe(false);
      expect(get(menu.isDuplicate)).toBe(false);
    });

    it('should fix the row group and report it back', () => {
      const { menu } = mountMenu();

      menu.confirmFixDuplicate();

      expect(confirmAndFixDuplicate).toHaveBeenCalledWith(['group-a'], expect.any(Function));
      const [, onDone] = confirmAndFixDuplicate.mock.calls[0];
      onDone();
      expect(onFixDuplicate).toHaveBeenCalledTimes(1);
    });

    it('should dismiss the row group and report it back', () => {
      const { menu } = mountMenu();

      menu.confirmIgnoreDuplicate();

      expect(confirmAndMarkNonDuplicated).toHaveBeenCalledWith(['group-a'], expect.any(Function));
      const [, onDone] = confirmAndMarkNonDuplicated.mock.calls[0];
      onDone();
      expect(onIgnoreDuplicate).toHaveBeenCalledTimes(1);
    });

    it('should do nothing when the row belongs to no group', () => {
      set(event, createEvent({ entryType: HistoryEventEntryType.EVM_EVENT, groupIdentifier: '' }));
      const { menu } = mountMenu();

      menu.confirmFixDuplicate();
      menu.confirmIgnoreDuplicate();

      expect(confirmAndFixDuplicate).not.toHaveBeenCalled();
      expect(confirmAndMarkNonDuplicated).not.toHaveBeenCalled();
    });
  });

  describe('adding an event next to the row', () => {
    it('should offer it for a row that stands for itself', () => {
      const { menu } = mountMenu();

      expect(get(menu.canAddEvent)).toBe(true);
    });

    it.each([
      HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
      HistoryEventEntryType.SWAP_EVENT,
    ])('should not offer it for a %s, which is edited as a group', (entryType) => {
      set(event, createEvent({ entryType }));
      const { menu } = mountMenu();

      expect(get(menu.canAddEvent)).toBe(false);
    });
  });

  describe('the transaction behind the row', () => {
    it('should read it off an evm event', () => {
      const { menu } = mountMenu();

      expect(get(menu.eventWithTxRef)).toStrictEqual({ location: 'ethereum', txRef: '0xabc' });
    });

    it('should read it off a solana event', () => {
      set(event, solanaEvent);
      const { menu } = mountMenu();

      expect(get(menu.eventWithTxRef)).toStrictEqual({ location: 'solana', txRef: 'sol-sig' });
    });

    it('should read it off an exchange event that carries one', () => {
      set(event, createEvent({
        entryType: HistoryEventEntryType.HISTORY_EVENT,
        location: 'kraken',
        txRef: 'withdrawal-ref',
      }));
      const { menu } = mountMenu();

      expect(get(menu.eventWithTxRef)).toStrictEqual({ location: 'kraken', txRef: 'withdrawal-ref' });
    });

    it('should find none on an exchange event without one', () => {
      set(event, onlineEvent);
      const { menu } = mountMenu();

      expect(get(menu.eventWithTxRef)).toBeUndefined();
    });

    it('should find none on a block event', () => {
      set(event, blockEvent);
      const { menu } = mountMenu();

      expect(get(menu.eventWithTxRef)).toBeUndefined();
    });
  });

  describe('what a re-decode would run on', () => {
    it('should use the row itself when the row can decode', () => {
      const { menu } = mountMenu();

      expect(get(menu.eventWithDecoding)).toBe(evmEvent);
      expect(get(menu.decodableEvmEvent)).toBe(evmEvent);
    });

    it('should fall back to the first child that can decode', () => {
      set(event, onlineEvent);
      set(groupEvents, [onlineEvent, solanaEvent, evmEvent]);
      const { menu } = mountMenu();

      expect(get(menu.eventWithDecoding)).toBe(solanaEvent);
    });

    it('should offer no decode options for a solana event', () => {
      set(event, solanaEvent);
      const { menu } = mountMenu();

      expect(get(menu.eventWithDecoding)).toBe(solanaEvent);
      expect(get(menu.decodableEvmEvent)).toBeUndefined();
    });

    it('should find nothing when neither the row nor its group can decode', () => {
      set(event, onlineEvent);
      set(groupEvents, [onlineEvent, blockEvent]);
      const { menu } = mountMenu();

      expect(get(menu.eventWithDecoding)).toBeUndefined();
      expect(get(menu.decodableEvmEvent)).toBeUndefined();
    });

    it('should find nothing when the row has no group to search', () => {
      set(event, onlineEvent);
      const { menu } = mountMenu();

      expect(get(menu.eventWithDecoding)).toBeUndefined();
    });

    it('should name a block event re-decode by its block number', () => {
      const { menu } = mountMenu();

      expect(menu.toRedecodePayload(decodableBlock)).toStrictEqual({
        data: [1234],
        type: HistoryEventEntryType.ETH_BLOCK_EVENT,
      });
    });

    it('should name every other re-decode by its location and transaction', () => {
      const { menu } = mountMenu();

      expect(menu.toRedecodePayload(decodableEvm)).toStrictEqual({
        data: { location: 'ethereum', txRef: '0xabc' },
        type: HistoryEventEntryType.EVM_EVENT,
      });
    });
  });

  describe('deleting the row', () => {
    it('should offer the events delete only when there is no transaction and no block', () => {
      set(event, onlineEvent);
      const { menu } = mountMenu();

      expect(get(menu.canDeleteEvents)).toBe(true);
    });

    it('should not offer it when the row belongs to a transaction', () => {
      const { menu } = mountMenu();

      expect(get(menu.canDeleteEvents)).toBe(false);
    });

    it('should not offer it for a block event', () => {
      set(event, blockEvent);
      const { menu } = mountMenu();

      expect(get(menu.canDeleteEvents)).toBe(false);
    });

    it('should delete the whole group when the row stands for one', () => {
      set(groupEvents, [createEvent({ identifier: 7 }), createEvent({ identifier: 9 })]);
      const { menu } = mountMenu();

      expect(menu.deletableEventIds()).toStrictEqual([7, 9]);
    });

    it('should delete only the row when it stands for itself', () => {
      set(event, createEvent({ entryType: HistoryEventEntryType.HISTORY_EVENT, identifier: 42 }));
      const { menu } = mountMenu();

      expect(menu.deletableEventIds()).toStrictEqual([42]);
    });
  });

  describe('reporting an issue', () => {
    it('should name the transaction the row belongs to', () => {
      const { menu } = mountMenu();

      menu.openReportDialog();

      const [{ description, title }] = showReportIssue.mock.calls[0];
      expect(title).toBe('actions.history_events.report_issue.title');
      expect(description).toContain('actions.history_events.report_issue.tx_hash::0xabc');
      expect(description).toContain('actions.history_events.report_issue.location::ethereum');
    });

    it('should leave the transaction line out when the row has none', () => {
      set(event, onlineEvent);
      const { menu } = mountMenu();

      menu.openReportDialog();

      const [{ description }] = showReportIssue.mock.calls[0];
      expect(description).not.toContain('actions.history_events.report_issue.tx_hash');
      expect(description).toContain('actions.history_events.report_issue.location::kraken');
    });
  });

  describe('the decode already in flight', () => {
    it('should forward both decoding flags', () => {
      set(ethBlockEventsDecoding, true);
      const { menu } = mountMenu();

      expect(get(menu.ethBlockEventsDecoding)).toBe(true);
      expect(get(menu.txEventsDecoding)).toBe(false);
    });
  });
});
