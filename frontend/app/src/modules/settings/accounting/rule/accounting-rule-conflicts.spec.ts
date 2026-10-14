import { describe, expect, it } from 'vitest';
import { propertyDiffers } from '@/modules/settings/accounting/rule/accounting-rule-conflicts';
import { type AccountingRule, type AccountingRuleConflict, AccountingTreatment } from '@/modules/settings/types/accounting';

function rule(overrides: Partial<AccountingRule> = {}): AccountingRule {
  return {
    accountingTreatment: null,
    counterparty: null,
    countCostBasisPnl: { value: true },
    countEntireAmountSpend: { value: true },
    eventSubtype: 'receive',
    eventType: 'receive',
    taxable: { value: true },
    ...overrides,
  };
}

function conflict(remote: Partial<AccountingRule>): AccountingRuleConflict {
  return { localData: rule(), localId: 1, remoteData: rule(remote) };
}

describe('propertyDiffers', () => {
  it('should find no difference between identical versions', () => {
    const same = conflict({});

    expect(propertyDiffers(same, 'taxable')).toBe(false);
    expect(propertyDiffers(same, 'accountingTreatment')).toBe(false);
  });

  it('should find a differing switch value', () => {
    expect(propertyDiffers(conflict({ taxable: { value: false } }), 'taxable')).toBe(true);
  });

  it('should keep a difference to its own property', () => {
    expect(propertyDiffers(conflict({ taxable: { value: false } }), 'countCostBasisPnl')).toBe(false);
  });

  it('should find versions that follow different settings even when the values match', () => {
    const linked = conflict({ countEntireAmountSpend: { linkedSetting: 'include_gas_costs', value: true } });

    expect(propertyDiffers(linked, 'countEntireAmountSpend')).toBe(true);
  });

  it('should find a differing accounting treatment', () => {
    expect(propertyDiffers(conflict({ accountingTreatment: AccountingTreatment.SWAP }), 'accountingTreatment')).toBe(true);
  });
});
