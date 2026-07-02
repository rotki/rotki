import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { startPromise } from '@shared/utils';
import { Routes } from '@/router/routes';

interface UseRuleEventsLinkReturn {
  viewEvents: (rule: AccountingRuleEntry) => void;
}

/**
 * Navigates to the history events page with the filter pre-applied to the
 * accounting rule's event type, subtype, and counterparty, so a user can jump
 * from a rule to the events it governs.
 */
export function useRuleEventsLink(): UseRuleEventsLinkReturn {
  const router = useRouter();

  function viewEvents(rule: AccountingRuleEntry): void {
    const query: Record<string, string> = {
      eventSubtypes: rule.eventSubtype,
      eventTypes: rule.eventType,
    };
    if (rule.counterparty)
      query.counterparties = rule.counterparty;

    startPromise(router.push({ path: Routes.HISTORY_EVENTS.toString(), query }));
  }

  return { viewEvents };
}
