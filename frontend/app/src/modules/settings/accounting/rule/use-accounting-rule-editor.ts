import type { ComputedRef, Ref } from 'vue';
import type { AccountingRuleAction, AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { isRequestFailure, type RequestError } from '@/modules/core/api/request-result';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import {
  type AccountingRuleQuery,
  parseEventId,
  parseRuleIntent,
  parseRuleQuery,
} from '@/modules/settings/accounting/rule/accounting-rule-query';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';
import { getPlaceholderRule } from '@/modules/settings/settings-utils';

/**
 * The rules a deep link found for the event it names. Both may exist: an event can be governed by a
 * general rule for its type/subtype pair *and* by one written for that event alone, and the choice
 * between them is what the action dialog asks.
 */
interface ActionDialogContext {
  eventId: number;
  generalRule?: AccountingRuleEntry;
  eventSpecificRule?: AccountingRuleEntry;
  /** Why the rules could not be read; the dialog then offers no action, since it cannot tell which exist. */
  loadError?: RequestError;
  /**
   * The rule the link named, kept for a retry of a failed read: the route query it came from is
   * consumed once the dialog is dealt with, so it cannot be read back from there.
   */
  ruleQuery?: AccountingRuleQuery;
}

/** Everything the action dialog renders from, in one object rather than four parallel refs. */
interface ActionDialogState {
  open: boolean;
  context?: ActionDialogContext;
  hasGeneralRule: boolean;
  hasEventSpecificRule: boolean;
  eventIds?: number[];
  loadError?: RequestError;
}

interface UseAccountingRuleEditorReturn {
  /** The rule the form dialog edits; `undefined` closes it. */
  modelRule: Ref<AccountingRuleEntry | undefined>;
  modelEditMode: Ref<boolean>;
  modelEventIds: Ref<number[] | undefined>;
  actionDialog: ComputedRef<ActionDialogState>;
  add: (rule?: AccountingRuleEntry, eventIds?: number[]) => void;
  edit: (rule: AccountingRuleEntry, eventIds?: number[]) => void;
  closeActionDialog: () => void;
  /** Honours an `add-rule`/`edit-rule` deep link, if the route carries one. */
  applyRouteIntent: () => Promise<void>;
  handleRuleAction: (action: AccountingRuleAction) => Promise<void>;
  /** Reads the event's rules again after the action dialog could not read them. */
  retryActionDialog: () => Promise<void>;
}

/**
 * Opening the rule form, both from the table and from a deep link.
 *
 * Other pages link here to write or amend the rule governing an event (`?add-rule`, `?edit-rule`,
 * `?eventId`, plus the type/subtype/counterparty naming the rule). A link that names an event has
 * two possible rules behind it, so it opens the action dialog to ask which one is meant; a link
 * without one goes straight to the form. Every path consumes the query afterwards, so a reload does
 * not reopen what was already dealt with.
 */
export function useAccountingRuleEditor(): UseAccountingRuleEditorReturn {
  const router = useRouter();
  const route = useRoute();
  const { getAccountingRule, getAccountingRules } = useAccountingSettings();
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const failureMessage = useFailureMessage();

  const modelRule = ref<AccountingRuleEntry>();
  const modelEditMode = shallowRef<boolean>(false);
  const modelEventIds = ref<number[]>();

  const context = ref<ActionDialogContext>();
  const open = shallowRef<boolean>(false);

  const actionDialog = computed<ActionDialogState>(() => {
    const current = get(context);
    return {
      context: current,
      eventIds: current?.eventSpecificRule?.eventIds ?? undefined,
      hasEventSpecificRule: Boolean(current?.eventSpecificRule),
      hasGeneralRule: Boolean(current?.generalRule),
      loadError: current?.loadError,
      open: get(open),
    };
  });

  function add(rule?: AccountingRuleEntry, eventIds?: number[]): void {
    set(modelRule, rule ?? getPlaceholderRule());
    set(modelEditMode, false);
    set(modelEventIds, eventIds);
  }

  function edit(rule: AccountingRuleEntry, eventIds?: number[]): void {
    set(modelRule, rule);
    set(modelEditMode, true);
    set(modelEventIds, eventIds);
  }

  function closeActionDialog(): void {
    set(open, false);
  }

  /** Opens the form on a new rule pre-filled with whatever the link named. */
  function addFromQuery(ruleQuery: AccountingRuleQuery, eventIds?: number[]): void {
    add({ ...getPlaceholderRule(), ...ruleQuery }, eventIds);
  }

  async function consumeQuery(): Promise<void> {
    await router.replace({ query: {} });
  }

  /**
   * Opens the action dialog on a failed read of the event's rules, offering no action, since which
   * rules exist is unknown. A cancelled read, as on a logout, closes the dialog and drops the link,
   * so a retry that was cancelled does not leave the earlier failure on screen.
   */
  async function showReadFailure(eventId: number, ruleQuery: AccountingRuleQuery, error: RequestError): Promise<void> {
    if (!isRequestFailure(error)) {
      set(open, false);
      await consumeQuery();
      return;
    }
    set(context, { eventId, loadError: error, ruleQuery });
    set(open, true);
  }

  /** Looks up both rules an event may have, then asks which of them the user meant. */
  async function askWhichRule(eventId: number, ruleQuery: AccountingRuleQuery): Promise<void> {
    const [generalRule, eventSpecificRules] = await Promise.all([
      getAccountingRule({
        eventSubtypes: [ruleQuery.eventSubtype],
        eventTypes: [ruleQuery.eventType],
        limit: 2,
        offset: 0,
      }, ruleQuery.counterparty),
      getAccountingRules({
        eventIds: [eventId],
        limit: 10,
        offset: 0,
      }),
    ]);

    if (!generalRule.ok) {
      await showReadFailure(eventId, ruleQuery, generalRule.error);
      return;
    }
    if (!eventSpecificRules.ok) {
      await showReadFailure(eventId, ruleQuery, eventSpecificRules.error);
      return;
    }

    set(context, {
      eventId,
      eventSpecificRule: eventSpecificRules.value.data.at(0),
      generalRule: generalRule.value,
    });
    set(open, true);
  }

  async function applyRouteIntent(): Promise<void> {
    const { query } = get(route);
    const intent = parseRuleIntent(query);
    if (!intent)
      return;

    const ruleQuery = parseRuleQuery(query);
    const eventId = parseEventId(query);

    if (intent === 'add') {
      if (eventId !== undefined) {
        set(context, { eventId });
        set(open, true);
        return;
      }

      addFromQuery(ruleQuery);
      await consumeQuery();
      return;
    }

    if (eventId !== undefined) {
      await askWhichRule(eventId, ruleQuery);
      return;
    }

    const rule = await getAccountingRule({
      eventSubtypes: [ruleQuery.eventSubtype],
      eventTypes: [ruleQuery.eventType],
      limit: 2,
      offset: 0,
    }, ruleQuery.counterparty);

    if (rule.ok && rule.value)
      edit(rule.value);
    else if (!rule.ok && isRequestFailure(rule.error))
      notifyRuleReadFailure(rule.error);

    await consumeQuery();
  }

  /** A link that only edits has no dialog open to show a failed read, so it is the one place that toasts. */
  function notifyRuleReadFailure(error: RequestError): void {
    notifyError(
      t('accounting_settings.rule.fetch_error.title'),
      t('accounting_settings.rule.fetch_error.message', { message: failureMessage(error) }),
    );
  }

  async function retryActionDialog(): Promise<void> {
    const current = get(context);
    if (current?.ruleQuery)
      await askWhichRule(current.eventId, current.ruleQuery);
  }

  async function handleRuleAction(action: AccountingRuleAction): Promise<void> {
    const current = get(context);
    if (!current)
      return;

    const { eventId, eventSpecificRule, generalRule } = current;
    const ruleQuery = parseRuleQuery(get(route).query);

    switch (action) {
      case 'add-general':
        addFromQuery(ruleQuery);
        break;
      case 'add-event-specific':
        addFromQuery(ruleQuery, [eventId]);
        break;
      case 'edit-general':
        if (generalRule)
          edit(generalRule);
        break;
      case 'edit-event-specific':
        if (eventSpecificRule)
          edit(eventSpecificRule, eventSpecificRule.eventIds ?? undefined);
        break;
    }

    closeActionDialog();
    await consumeQuery();
  }

  return {
    actionDialog,
    add,
    applyRouteIntent,
    closeActionDialog,
    edit,
    handleRuleAction,
    modelEditMode,
    modelEventIds,
    modelRule,
    retryActionDialog,
  };
}
