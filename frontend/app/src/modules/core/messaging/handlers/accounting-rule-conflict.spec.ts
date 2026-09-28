import { describe, expect, it, vi } from 'vitest';
import { createAccountingRuleConflictHandler } from './accounting-rule-conflict';

const { refresh } = vi.hoisted(() => ({ refresh: vi.fn() }));

vi.mock('@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count', () => ({
  useAccountingRuleConflictsCount: (): Record<string, unknown> => ({ refresh }),
}));

describe('modules/core/messaging/handlers/accounting-rule-conflict', () => {
  it('should re-read the conflicts the action center counts, and post no notification', async () => {
    const handler = createAccountingRuleConflictHandler();

    const result = await handler.handle({ numOfConflicts: 2 });

    expect(refresh).toHaveBeenCalledOnce();
    expect(result).toBeUndefined();
  });
});
