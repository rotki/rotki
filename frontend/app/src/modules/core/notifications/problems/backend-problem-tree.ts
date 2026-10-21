import type { UserMessageData, UserMessageKey } from '@/modules/core/messaging/types/base';

/** A backend user message the drawer files: every family but `auth`, which raises a condition instead. */
export type ProblemMessage = Exclude<UserMessageData, { key: typeof UserMessageKey.AUTH }>;

export const BALANCE_SNAPSHOT = 'balance_snapshot';

/** A balance snapshot that failed to save, filed as its own family beside the user messages. */
interface SnapshotProblem {
  readonly key: typeof BALANCE_SNAPSHOT;
  readonly fields: { readonly error: string };
  readonly subject: string;
  readonly value: string;
  readonly verbosity: 'error';
}

/** What one item was last reported as, discriminated on its family `key`. */
export type ProblemSource = ProblemMessage | SnapshotProblem;

export type ProblemFamily = ProblemSource['key'];

/** Most items a parent keeps; older ones are dropped and only counted. */
export const MAX_ITEMS_PER_PROBLEM = 50;

/** One problem: the backend's `group`, folding every repeat of it. */
export interface ProblemItem {
  readonly identity: string;
  /** The newest report of it, whose `value` and `error` back "copy details". */
  readonly source: ProblemSource;
  readonly repeats: number;
  readonly firstSeen: Date;
  readonly lastSeen: Date;
}

/** One family on one location at one verbosity, holding the distinct problems under it. */
export interface BackendProblem {
  readonly id: string;
  readonly key: ProblemFamily;
  readonly verbosity: ProblemSource['verbosity'];
  readonly subject: string | null;
  /** Newest first, at most {@link MAX_ITEMS_PER_PROBLEM}. */
  readonly items: readonly ProblemItem[];
  /** Distinct items seen, including the ones dropped past the cap. */
  readonly itemTotal: number;
  /** Every report folded into this parent. */
  readonly repeats: number;
  readonly firstSeen: Date;
  readonly lastSeen: Date;
  /** Whether the drawer has been opened since a new item arrived. */
  readonly read: boolean;
}

/** One report to fold into the tree. */
export interface ProblemReport {
  readonly source: ProblemSource;
  /** The item's identity within its parent. */
  readonly identity: string;
  /** How many sends this report stands for: more than one for repeats the backend held. */
  readonly count: number;
  /** When it was sent. */
  readonly at: Date;
}

function problemId(source: ProblemSource): string {
  return JSON.stringify([source.verbosity, source.key, source.subject]);
}

function earlier(a: Date, b: Date): Date {
  return a < b ? a : b;
}

function later(a: Date, b: Date): Date {
  return a > b ? a : b;
}

function newItem(report: ProblemReport): ProblemItem {
  return {
    firstSeen: report.at,
    identity: report.identity,
    lastSeen: report.at,
    repeats: report.count,
    source: report.source,
  };
}

/**
 * Folds a report into an existing item.
 *
 * @remarks
 * A report the backend held can be older than what the item already shows, such as one a dying
 * connection never delivered, handed back after a newer one arrived live. The item keeps the newer
 * source and never moves back in time.
 */
function foldItem(item: ProblemItem, report: ProblemReport): ProblemItem {
  const isNewer = report.at >= item.lastSeen;
  return {
    firstSeen: earlier(item.firstSeen, report.at),
    identity: item.identity,
    lastSeen: later(item.lastSeen, report.at),
    repeats: item.repeats + report.count,
    source: isNewer ? report.source : item.source,
  };
}

function byLastSeen(a: { lastSeen: Date }, b: { lastSeen: Date }): number {
  return b.lastSeen.getTime() - a.lastSeen.getTime();
}

function newProblem(report: ProblemReport): BackendProblem {
  const { source } = report;
  return {
    firstSeen: report.at,
    id: problemId(source),
    itemTotal: 1,
    items: [newItem(report)],
    key: source.key,
    lastSeen: report.at,
    read: false,
    repeats: report.count,
    subject: source.subject,
    verbosity: source.verbosity,
  };
}

/**
 * Folds a report into its parent.
 *
 * @remarks
 * A new item marks the parent unread, since it is a problem the user has not seen; a repeat of a
 * known item does not. An item dropped past the cap that comes back counts as new again.
 */
function foldProblem(problem: BackendProblem, report: ProblemReport): BackendProblem {
  const index = problem.items.findIndex(item => item.identity === report.identity);
  const isNewItem = index === -1;
  const items = [...problem.items];

  if (isNewItem)
    items.push(newItem(report));
  else
    items[index] = foldItem(items[index], report);

  return {
    ...problem,
    firstSeen: earlier(problem.firstSeen, report.at),
    itemTotal: problem.itemTotal + (isNewItem ? 1 : 0),
    items: items.sort(byLastSeen).slice(0, MAX_ITEMS_PER_PROBLEM),
    lastSeen: later(problem.lastSeen, report.at),
    read: problem.read && !isNewItem,
    repeats: problem.repeats + report.count,
  };
}

/**
 * The tree without the items `matches` picks, for problems the user has since fixed, newest
 * parent first.
 *
 * @remarks
 * A parent loses the removed items from its counts and is dropped once it has none left to show.
 * Its last sighting becomes the newest remaining item's, which is exact because the cap keeps the
 * newest items. Its first sighting is recomputed only when no item is hidden past the cap, since a
 * hidden one may be older still.
 */
export function withoutItems(problems: readonly BackendProblem[], matches: (item: ProblemItem) => boolean): BackendProblem[] {
  return problems.flatMap((problem) => {
    const removed = problem.items.filter(matches);
    if (removed.length === 0)
      return [problem];

    const items = problem.items.filter(item => !matches(item));
    if (items.length === 0)
      return [];

    const itemTotal = problem.itemTotal - removed.length;
    const hasHiddenItems = itemTotal > items.length;
    return [{
      ...problem,
      firstSeen: hasHiddenItems ? problem.firstSeen : items.map(item => item.firstSeen).reduce(earlier),
      itemTotal,
      items,
      lastSeen: items.map(item => item.lastSeen).reduce(later),
      repeats: problem.repeats - removed.reduce((sum, item) => sum + item.repeats, 0),
    }];
  }).sort(byLastSeen);
}

/**
 * The tree with one more report folded in, newest parent first.
 *
 * @remarks
 * Parents need no cap of their own: there is one per verbosity, family and location, all of them
 * finite, while the items under each are capped.
 */
export function foldReport(problems: readonly BackendProblem[], report: ProblemReport): BackendProblem[] {
  const id = problemId(report.source);
  const existing = problems.find(problem => problem.id === id);
  const folded = existing ? foldProblem(existing, report) : newProblem(report);
  return [folded, ...problems.filter(problem => problem.id !== id)].sort(byLastSeen);
}
