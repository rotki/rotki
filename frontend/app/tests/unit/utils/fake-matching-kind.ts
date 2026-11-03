import type { MatchingKind } from '@/modules/history/events/matching/matching-kind';
import type { MatchingFlow, PotentialMatchEntryLabels, UnmatchedEventGroup } from '@/modules/history/events/matching/types';
import { vi } from 'vitest';
import { computed } from 'vue';
import { assetMovementMatchingKind } from '@/modules/history/events/matching/asset-movement-matching-kind';
import { bridgeMatchingKind } from '@/modules/history/events/matching/bridge-matching-kind';

/** A real kind whose pinned tab and messages a fake borrows, named for the spec title. */
export interface FakeMatchingKindCase {
  name: string;
  real: Pick<MatchingKind<UnmatchedEventGroup>, 'messages' | 'pinnedName'>;
}

/** What a fake kind hands out, so a spec can assert each value arrived where it belongs. */
interface FakeMatchingKind {
  kind: MatchingKind<UnmatchedEventGroup>;
  flow: MatchingFlow;
  entryLabels: PotentialMatchEntryLabels;
  explanation: string;
  /** Every getter a subject composable was handed, to check they read the right item. */
  subjects: (() => UnmatchedEventGroup | undefined)[];
}

/**
 * A matching kind for specs of the panels that only pass a kind's dialog members along: its
 * pinned tab, messages, flow, entry labels and unmatchable explanation.
 *
 * @remarks
 * The pinned tab and messages come from a real kind, the rest are unique to the case, so two
 * fakes built from different cases differ in every one of those members and a panel that reads
 * one from the wrong place, or hardcodes one kind's value, fails for at least one of them. The
 * list and content members are inert stubs; specs of those panels use the real kinds.
 */
export function fakeMatchingKind({ name, real }: FakeMatchingKindCase): FakeMatchingKind {
  const flow: MatchingFlow = {
    getSuggestions: vi.fn().mockResolvedValue({ closeMatches: [], otherEvents: [] }),
    match: vi.fn().mockResolvedValue({ success: true }),
    refresh: vi.fn().mockResolvedValue(undefined),
  };
  const entryLabels: PotentialMatchEntryLabels = { locationHeader: `${name} location`, type: `${name} type` };
  const explanation = `${name} cannot be matched`;
  const subjects: (() => UnmatchedEventGroup | undefined)[] = [];

  const kind: MatchingKind<UnmatchedEventGroup> = {
    bulkSelection: { hideWhenEmpty: false, needsTier: false },
    getIdentifier: vi.fn(),
    messages: real.messages,
    pinnedName: real.pinnedName,
    useActions: vi.fn(),
    useEntryLabels: (subject) => {
      subjects.push(subject);
      return computed<PotentialMatchEntryLabels>(() => entryLabels);
    },
    useFlow: () => flow,
    useRows: vi.fn(),
    useSource: vi.fn(),
    useUnmatchableExplanation: (subject) => {
      subjects.push(subject);
      return computed<string>(() => explanation);
    },
    variant: assetMovementMatchingKind.variant,
  };

  return { entryLabels, explanation, flow, kind, subjects };
}

/** Two cases borrowing each real kind's pinned tab and messages; build the fakes per test. */
export const FAKE_MATCHING_KIND_CASES: FakeMatchingKindCase[] = [
  { name: 'first', real: assetMovementMatchingKind },
  { name: 'second', real: bridgeMatchingKind },
];
