import type { APIRequestContext } from '@playwright/test';
import { backendUrl } from '../../../playwright.config';

/** One accounting rule to seed, reduced to the parts a test cares about. */
export interface SeedAccountingRule {
  eventType: string;
  eventSubtype: string;
  counterparty?: string | null;
}

/**
 * Writes accounting rules via the API, so a test about the rules table is guaranteed a rule of each
 * kind it asserts on.
 *
 * Idempotent: rotki's default rules are pulled from the data repo rather than created with the
 * account, so whether a given rule is already there depends on whether that pull has finished. A
 * rule that already exists is what the caller wanted anyway, so the conflict is not an error.
 */
export async function apiAddAccountingRules(
  request: APIRequestContext,
  rules: SeedAccountingRule[],
): Promise<void> {
  for (const rule of rules) {
    const response = await request.put(`${backendUrl}/api/1/accounting/rules`, {
      data: {
        accounting_treatment: null,
        count_cost_basis_pnl: { value: false },
        count_entire_amount_spend: { value: false },
        counterparty: rule.counterparty ?? null,
        event_subtype: rule.eventSubtype,
        event_type: rule.eventType,
        taxable: { value: true },
      },
      failOnStatusCode: false,
    });

    if (response.ok())
      continue;

    const body = await response.text();
    if (!body.includes('already exists'))
      throw new Error(`Failed to seed accounting rule ${rule.eventType}/${rule.eventSubtype}: ${body}`);
  }
}
