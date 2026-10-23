import { describe, expect, it } from 'vitest';
import {
  accountingRulesExportActivity,
  accountingRulesImportActivity,
  accountingRulesResetActivity,
} from '@/modules/settings/accounting/accounting-rules.activity';

describe('accounting rules activity ids', () => {
  it('should give export, import and reset their fixed ids', () => {
    expect(accountingRulesExportActivity.id()).toBe('accounting-rules:export');
    expect(accountingRulesImportActivity.id()).toBe('accounting-rules:import');
    expect(accountingRulesResetActivity.id()).toBe('accounting-rules:reset');
  });
});
