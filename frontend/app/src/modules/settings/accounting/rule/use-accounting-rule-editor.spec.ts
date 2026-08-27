import type { LocationQuery } from 'vue-router';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingRuleEditor } from '@/modules/settings/accounting/rule/use-accounting-rule-editor';

const replace = vi.fn(async (): Promise<void> => {});
let query: LocationQuery = {};

vi.mock('vue-router', () => ({
  useRoute: (): { query: LocationQuery } => ({ get query(): LocationQuery {
    return query;
  } }),
  useRouter: (): { replace: typeof replace } => ({ replace }),
}));

const getAccountingRule = vi.fn(async (): Promise<AccountingRuleEntry | undefined> => undefined);
const getAccountingRules = vi.fn(async (): Promise<{ data: AccountingRuleEntry[] }> => ({ data: [] }));

vi.mock('@/modules/settings/accounting/use-accounting-settings', () => ({
  useAccountingSettings: (): Record<string, unknown> => ({
    getAccountingRule,
    getAccountingRules,
  }),
}));

function buildRule(overrides: Partial<AccountingRuleEntry> = {}): AccountingRuleEntry {
  return {
    accountingTreatment: null,
    countCostBasisPnl: { value: false },
    countEntireAmountSpend: { value: false },
    counterparty: null,
    eventSubtype: 'fee',
    eventType: 'spend',
    identifier: 7,
    taxable: { value: false },
    ...overrides,
  };
}

describe('useAccountingRuleEditor', () => {
  beforeEach(() => {
    query = {};
    replace.mockClear();
    getAccountingRule.mockClear().mockResolvedValue(undefined);
    getAccountingRules.mockClear().mockResolvedValue({ data: [] });
  });

  describe('add and edit', () => {
    it('should open the form on a blank rule when nothing is passed', () => {
      const { add, modelEditMode, modelRule } = useAccountingRuleEditor();
      add();

      expect(get(modelRule)?.identifier).toBe(-1);
      expect(get(modelEditMode)).toBe(false);
    });

    it('should open the form on the rule being edited', () => {
      const { edit, modelEditMode, modelEventIds, modelRule } = useAccountingRuleEditor();
      edit(buildRule(), [3]);

      expect(get(modelRule)?.identifier).toBe(7);
      expect(get(modelEditMode)).toBe(true);
      expect(get(modelEventIds)).toStrictEqual([3]);
    });
  });

  describe('applyRouteIntent', () => {
    it('should do nothing when the route carries no intent', async () => {
      query = { eventType: 'spend' };
      const { applyRouteIntent, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(get(modelRule)).toBeUndefined();
      expect(getAccountingRule).not.toHaveBeenCalled();
      expect(replace).not.toHaveBeenCalled();
    });

    it('should open a new rule pre-filled from an add link', async () => {
      query = { 'add-rule': 'true', 'counterparty': 'aave-v3', 'eventSubtype': 'fee', 'eventType': 'spend' };
      const { applyRouteIntent, modelEditMode, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(get(modelRule)).toMatchObject({
        counterparty: 'aave-v3',
        eventSubtype: 'fee',
        eventType: 'spend',
        identifier: -1,
      });
      expect(get(modelEditMode)).toBe(false);
      // Consumed, so a reload does not reopen the form.
      expect(replace).toHaveBeenCalledWith({ query: {} });
    });

    it('should ask which rule to add when the add link names an event', async () => {
      query = { 'add-rule': 'true', 'eventId': '42' };
      const { actionDialog, applyRouteIntent } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(get(actionDialog)).toMatchObject({
        context: { eventId: 42 },
        hasEventSpecificRule: false,
        hasGeneralRule: false,
        open: true,
      });
      expect(getAccountingRule).not.toHaveBeenCalled();
      // Still needed by the action that follows, so it is consumed then, not now.
      expect(replace).not.toHaveBeenCalled();
    });

    it('should open the found rule from an edit link', async () => {
      query = { 'edit-rule': 'true', 'eventSubtype': 'fee', 'eventType': 'spend' };
      getAccountingRule.mockResolvedValue(buildRule());
      const { applyRouteIntent, modelEditMode, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(getAccountingRule).toHaveBeenCalledWith(
        { eventSubtypes: ['fee'], eventTypes: ['spend'], limit: 2, offset: 0 },
        null,
      );
      expect(get(modelRule)?.identifier).toBe(7);
      expect(get(modelEditMode)).toBe(true);
      expect(replace).toHaveBeenCalledWith({ query: {} });
    });

    it('should consume an edit link that matches no rule, without opening the form', async () => {
      query = { 'edit-rule': 'true', 'eventType': 'spend' };
      const { applyRouteIntent, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(get(modelRule)).toBeUndefined();
      expect(replace).toHaveBeenCalledWith({ query: {} });
    });

    it('should offer both the general rule and the event\'s own when the edit link names an event', async () => {
      query = { 'edit-rule': 'true', 'eventId': '42', 'eventSubtype': 'fee', 'eventType': 'spend' };
      getAccountingRule.mockResolvedValue(buildRule({ identifier: 1 }));
      getAccountingRules.mockResolvedValue({ data: [buildRule({ eventIds: [42], identifier: 2 })] });
      const { actionDialog, applyRouteIntent } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(getAccountingRules).toHaveBeenCalledWith({ eventIds: [42], limit: 10, offset: 0 });
      expect(get(actionDialog)).toMatchObject({
        eventIds: [42],
        hasEventSpecificRule: true,
        hasGeneralRule: true,
        open: true,
      });
    });

    it('should report only the general rule when the event has none of its own', async () => {
      query = { 'edit-rule': 'true', 'eventId': '42', 'eventType': 'spend' };
      getAccountingRule.mockResolvedValue(buildRule());
      const { actionDialog, applyRouteIntent } = useAccountingRuleEditor();
      await applyRouteIntent();

      expect(get(actionDialog)).toMatchObject({
        eventIds: undefined,
        hasEventSpecificRule: false,
        hasGeneralRule: true,
      });
    });
  });

  describe('handleRuleAction', () => {
    it('should do nothing when no dialog is open', async () => {
      const { handleRuleAction, modelRule } = useAccountingRuleEditor();
      await handleRuleAction('add-general');

      expect(get(modelRule)).toBeUndefined();
      expect(replace).not.toHaveBeenCalled();
    });

    it('should bind a new rule to the event when the event-specific one is chosen', async () => {
      query = { 'add-rule': 'true', 'eventId': '42', 'eventType': 'spend' };
      const { actionDialog, applyRouteIntent, handleRuleAction, modelEventIds, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();
      await handleRuleAction('add-event-specific');

      expect(get(modelRule)).toMatchObject({ eventType: 'spend', identifier: -1 });
      expect(get(modelEventIds)).toStrictEqual([42]);
      expect(get(actionDialog).open).toBe(false);
      expect(replace).toHaveBeenCalledWith({ query: {} });
    });

    it('should edit the general rule when that is chosen', async () => {
      query = { 'edit-rule': 'true', 'eventId': '42', 'eventType': 'spend' };
      getAccountingRule.mockResolvedValue(buildRule({ identifier: 1 }));
      const { applyRouteIntent, handleRuleAction, modelEditMode, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();
      await handleRuleAction('edit-general');

      expect(get(modelRule)?.identifier).toBe(1);
      expect(get(modelEditMode)).toBe(true);
    });

    it('should close and consume the query without opening a form when the chosen rule is missing', async () => {
      query = { 'edit-rule': 'true', 'eventId': '42', 'eventType': 'spend' };
      const { actionDialog, applyRouteIntent, handleRuleAction, modelRule } = useAccountingRuleEditor();
      await applyRouteIntent();
      await handleRuleAction('edit-event-specific');

      expect(get(modelRule)).toBeUndefined();
      expect(get(actionDialog).open).toBe(false);
      expect(replace).toHaveBeenCalledWith({ query: {} });
    });
  });
});
