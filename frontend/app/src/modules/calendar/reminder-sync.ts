/** A reminder as the server holds it. */
export interface StoredReminder {
  identifier: number;
  secsBefore: number;
}

/** A row as the user has left it. Without an `identifier` it is one they added in this session. */
export interface ReminderDraft {
  identifier?: number;
  secsBefore: number;
}

interface ReminderUpdate {
  identifier: number;
  secsBefore: number;
}

export interface ReminderPlan {
  /** Intervals to create, already deduplicated against each other and against the kept rows. */
  added: number[];
  /** Identifiers to remove. */
  deleted: number[];
  updated: ReminderUpdate[];
}

/**
 * Works out what a set of edited rows means for the stored reminders.
 *
 * Reminders used to be written one at a time as each row was left, which meant a new event and an
 * existing one took different paths and a row could reach the server before the user pressed save.
 * The rows are now ordinary form state in both cases, and this turns the final state into the calls
 * that reconcile it, so the dialog persists once and only on save.
 *
 * An event has no use for two reminders at the same interval, so a new row that duplicates one
 * being kept is dropped rather than sent.
 */
/** A draft still backed by a stored reminder, paired with the reminder it edits. */
function pairWithStored(
  drafts: readonly ReminderDraft[],
  storedById: ReadonlyMap<number, StoredReminder>,
): { current: StoredReminder; draft: ReminderDraft }[] {
  const pairs: { current: StoredReminder; draft: ReminderDraft }[] = [];

  for (const draft of drafts) {
    if (draft.identifier === undefined)
      continue;

    const current = storedById.get(draft.identifier);
    // Its reminder is gone, so the row counts as a new one instead.
    if (current !== undefined)
      pairs.push({ current, draft });
  }

  return pairs;
}

export function planReminderSync(
  stored: readonly StoredReminder[],
  drafts: readonly ReminderDraft[],
): ReminderPlan {
  const storedById = new Map<number, StoredReminder>(stored.map(item => [item.identifier, item]));
  const kept = pairWithStored(drafts, storedById);
  const keptDrafts = new Set<ReminderDraft>(kept.map(pair => pair.draft));
  const keptIds = new Set<number>(kept.map(pair => pair.current.identifier));

  const deleted = stored
    .filter(item => !keptIds.has(item.identifier))
    .map(item => item.identifier);

  const updated: ReminderUpdate[] = kept
    .filter(({ current, draft }) => current.secsBefore !== draft.secsBefore)
    .map(({ current, draft }) => ({ identifier: current.identifier, secsBefore: draft.secsBefore }));

  // The intervals that will exist once the kept rows are written, so a new row cannot duplicate one.
  const occupied = new Set<number>(kept.map(pair => pair.draft.secsBefore));

  const added: number[] = [];
  for (const draft of drafts) {
    if (keptDrafts.has(draft) || occupied.has(draft.secsBefore))
      continue;

    occupied.add(draft.secsBefore);
    added.push(draft.secsBefore);
  }

  return { added, deleted, updated };
}
