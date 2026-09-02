import type { ComputedRef, Ref } from 'vue';
import type { AccountingRuleAction, AccountingRuleEntry } from '@/modules/settings/types/accounting';
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
}

/** Everything the action dialog renders from, in one object rather than four parallel refs. */
interface ActionDialogState {
  open: boolean;
  context?: ActionDialogContext;
  hasGeneralRule: boolean;
  hasEventSpecificRule: boolean;
  eventIds?: number[];
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

    set(context, {
      eventId,
      eventSpecificRule: eventSpecificRules.data.at(0),
      generalRule,
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

    if (rule)
      edit(rule);

    await consumeQuery();
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
  };
}
