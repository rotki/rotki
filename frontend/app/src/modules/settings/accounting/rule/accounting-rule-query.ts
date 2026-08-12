import type { LocationQuery } from 'vue-router';
import { z } from 'zod';

/** Which half of the rules the table shows, sent to the backend as `customRuleHandling`. */
export const CustomRuleHandling = {
  /** Show regular rules (exclude event-specific rules) */
  EXCLUDE: 'exclude',
  /** Show only event-specific rules */
  ONLY: 'only',
} as const;

export type CustomRuleHandling = typeof CustomRuleHandling[keyof typeof CustomRuleHandling];

const customRuleHandlings: string[] = Object.values(CustomRuleHandling);

/** Whether a raw value (a url the user can write by hand) names a handling the backend takes. */
export function isCustomRuleHandling(value: string): value is CustomRuleHandling {
  return customRuleHandlings.includes(value);
}

/**
 * The rule a deep link names. Every field is optional on the wire — the link is written by other
 * pages (an event asking for the rule that governs it), so the schema defaults rather than throws
 * and a half-written link still opens the form with what it did carry.
 */
export const AccountingRuleQuerySchema = z.object({
  counterparty: z.string().nullable().default(null),
  eventSubtype: z.string().default(''),
  eventType: z.string().default(''),
});

export type AccountingRuleQuery = z.infer<typeof AccountingRuleQuerySchema>;

/**
 * Reads the rule a route names. Takes the query rather than the route so it stays pure: the whole
 * deep-link surface is decided by this one object, and testing it needs no router.
 *
 * A repeated parameter arrives as an array, which is neither a rule identity nor something the
 * form can use, so it is dropped in favour of the schema's default.
 */
export function parseRuleQuery(query: LocationQuery): AccountingRuleQuery {
  return AccountingRuleQuerySchema.parse({
    counterparty: single(query.counterparty),
    // Both are `z.string()`, whose default only covers `undefined`. A valueless parameter
    // (`?eventType`) parses as `null`, which would otherwise be an invalid_type error thrown from
    // inside `onMounted`, leaving the table empty for the rest of the session.
    eventSubtype: single(query.eventSubtype) ?? undefined,
    eventType: single(query.eventType) ?? undefined,
  });
}

/**
 * Reads the event a deep link points at, or nothing when it names none or names nonsense.
 *
 * Identifiers start at 1, so anything below that is not an event: `Number('')` and `Number(' ')`
 * are both a finite 0, which would otherwise open the "which rule did you mean" dialog for an
 * event that does not exist.
 */
export function parseEventId(query: LocationQuery): number | undefined {
  const value = single(query.eventId);
  if (value === undefined || value === null)
    return undefined;

  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : undefined;
}

/** Which of the two deep-link intents a route carries, if any. */
export function parseRuleIntent(query: LocationQuery): 'add' | 'edit' | undefined {
  if (query['add-rule'])
    return 'add';
  if (query['edit-rule'])
    return 'edit';
  return undefined;
}

function single(value: LocationQuery[string]): string | null | undefined {
  return Array.isArray(value) ? undefined : value;
}
