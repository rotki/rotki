import type { MessageKey } from '@/message-key';
import { createCustomPinia } from '@test/utils/create-pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import en from '@/locales/en.json';
import {
  type BackendProblem,
  BALANCE_SNAPSHOT,
  foldReport,
  type ProblemItem,
  type ProblemSource,
} from '@/modules/core/notifications/problems/backend-problem-tree';
import {
  ENTRY_LABELS,
  FEATURE_LABELS,
  OPERATION_LABELS,
  RECORD_LABELS,
  UserMessageEntry,
  UserMessageFeature,
  UserMessageOperation,
  UserMessageRecord,
} from '@/modules/core/notifications/problems/backend-problem-vocabulary';
import { useBackendProblemText } from '@/modules/core/notifications/problems/use-backend-problem-text';

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): { getLocationData: (id: string) => { name: string } | undefined } => ({
    getLocationData: (id: string) => (id === 'kucoin' ? { name: 'KuCoin' } : undefined),
  }),
}));

const AT = new Date('2026-09-30T07:00:00Z');

function filed(source: ProblemSource): { problem: BackendProblem; item: ProblemItem } {
  const [problem] = foldReport([], { at: AT, count: 1, identity: 'identity', source });
  return { item: problem.items[0], problem };
}

/**
 * Whether en.json has a message at a dotted key, by presence: the i18n plugin compiles a leaf into
 * a node rather than a string.
 */
function hasMessage(key: string): boolean {
  let node: unknown = en;
  for (const part of key.split('.'))
    node = typeof node === 'object' && node !== null && part in node ? Reflect.get(node, part) : undefined;
  return node !== undefined;
}

describe('useBackendProblemText', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  describe('labels', () => {
    it.each([
      ['record', RECORD_LABELS, UserMessageRecord],
      ['entry', ENTRY_LABELS, UserMessageEntry],
      ['operation', OPERATION_LABELS, UserMessageOperation],
      ['feature', FEATURE_LABELS, UserMessageFeature],
    ] satisfies [string, Record<string, MessageKey>, Record<string, string>][])(
      'should have an english label for every %s',
      (_name, labels, vocabulary) => {
        for (const value of Object.values(vocabulary)) {
          const key = new Map<string, MessageKey>(Object.entries(labels)).get(value);
          expect(key && hasMessage(key), value).toBe(true);
        }
      },
    );
  });

  describe('problemTitle', () => {
    it('should name the family and the location', () => {
      const { problem } = filed({ fields: { entry: 'tag' }, group: [], key: 'local_db', subject: 'kucoin', value: 'v', verbosity: 'error' });

      expect(useBackendProblemText().problemTitle(problem))
        .toBe('backend_problems.with_subject::KuCoin, backend_problems.title.local_db');
    });

    it('should name the family alone for a problem about no location', () => {
      const { problem } = filed({ fields: { entry: 'tag' }, group: [], key: 'local_db', subject: null, value: 'v', verbosity: 'error' });

      expect(useBackendProblemText().problemTitle(problem)).toBe('backend_problems.title.local_db');
    });

    it('should title a failed snapshot as its own family', () => {
      const { problem } = filed({ fields: { error: 'e' }, key: BALANCE_SNAPSHOT, subject: 'kraken', value: 'v', verbosity: 'error' });

      expect(useBackendProblemText().problemTitle(problem))
        .toBe('backend_problems.with_subject::Kraken, backend_problems.title.balance_snapshot');
    });
  });

  describe('itemHeading', () => {
    it('should label an item by its vocabulary value', () => {
      const { item } = filed({ fields: { error: 'e', record: 'trade' }, group: [], key: 'network', subject: null, value: 'v', verbosity: 'error' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ kind: 'text', text: 'backend_problems.record.trade' });
    });

    it('should fall back to the backend sentence for a value this build does not know', () => {
      const { item } = filed({ fields: { feature: 'time_travel' }, group: [], key: 'unsupported', subject: null, value: 'Time travel is not supported', verbosity: 'warning' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ kind: 'text', text: 'Time travel is not supported' });
    });

    it('should head a missing price with its asset and time', () => {
      const { item } = filed({ fields: { asset: 'ETH', timestamp: 1700000000 }, group: [], key: 'price', subject: null, value: 'v', verbosity: 'warning' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ asset: 'ETH', kind: 'asset', timestamp: 1700000000 });
    });

    it('should head a missing price for no single asset as a batch', () => {
      const { item } = filed({ fields: { asset: null, timestamp: null }, group: [], key: 'price', subject: null, value: 'v', verbosity: 'warning' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ kind: 'text', text: 'backend_problems.price_batch' });
    });

    it('should head an unknown asset with its identifier', () => {
      const { item } = filed({ fields: { identifier: '1234' }, group: [], key: 'unknown_asset', subject: 'bitpanda', value: 'v', verbosity: 'warning' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ full: '1234', kind: 'text', text: '1234' });
    });

    it('should shorten an unknown token in the middle of its address, so tokens of one chain stay apart', () => {
      const identifier = 'eip155:1/erc20:0x6B175474E89094C44Da98b954EedeAC495271d0F';
      const { item } = filed({ fields: { identifier }, group: [], key: 'unknown_asset', subject: 'binance', value: 'v', verbosity: 'warning' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ full: identifier, kind: 'text', text: 'eip155:1/erc20:0x6B17...1d0F' });
    });

    it('should head a failed snapshot with when it failed', () => {
      const { item } = filed({ fields: { error: 'e' }, key: BALANCE_SNAPSHOT, subject: 'kraken', value: 'v', verbosity: 'error' });

      expect(useBackendProblemText().itemHeading(item)).toEqual({ date: AT, kind: 'date' });
    });
  });

  describe('itemDetails', () => {
    it('should add the error when the sentence leaves it out', () => {
      const { item } = filed({ fields: { error: 'HTTP 502', record: 'trade' }, group: [], key: 'network', subject: null, value: 'Could not query trades', verbosity: 'error' });

      expect(useBackendProblemText().itemDetails(item)).toBe('Could not query trades\nHTTP 502');
    });

    it('should not repeat an error the sentence already carries', () => {
      const { item } = filed({ fields: { error: 'HTTP 502', record: 'trade' }, group: [], key: 'network', subject: null, value: 'Could not query trades: HTTP 502', verbosity: 'error' });

      expect(useBackendProblemText().itemDetails(item)).toBe('Could not query trades: HTTP 502');
    });
  });
});
