import type { Router } from 'vue-router';
import { assert, NotificationGroup, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createOraclePenalizedHandler } from '@/modules/core/messaging/handlers/oracle-penalized';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

const push = vi.fn<Router['push']>();
const router = createMock<Router>({ push });

describe('createOraclePenalizedHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should build a warning that names the oracle and explains it stopped answering', async () => {
    const handler = createOraclePenalizedHandler(mockT, router);

    const result = await handler.handle({ oracle: 'coingecko', penaltyDuration: 1800, reason: 'timeout' });

    expect(result.severity).toBe(Severity.WARNING);
    expect(result.display).toBe(true);
    expect(result.message).toContain('message_timeout');
    expect(result.message).not.toContain('message_errors');
  });

  it('should explain repeated failures differently from a silent host', async () => {
    const handler = createOraclePenalizedHandler(mockT, router);

    const result = await handler.handle({ oracle: 'defillama', penaltyDuration: 1800, reason: 'errors' });

    expect(result.message).toContain('message_errors');
    expect(result.message).not.toContain('message_timeout');
  });

  it('should give each oracle its own group so two penalized oracles do not collapse into one', async () => {
    const handler = createOraclePenalizedHandler(mockT, router);

    const coingecko = await handler.handle({ oracle: 'coingecko', penaltyDuration: 1800, reason: 'timeout' });
    const defillama = await handler.handle({ oracle: 'defillama', penaltyDuration: 1800, reason: 'timeout' });

    expect(coingecko.group).toBe(`${NotificationGroup.ORACLE_PENALIZED}:coingecko`);
    expect(coingecko.group).not.toBe(defillama.group);
  });

  it('should route to the price oracle settings when the action is clicked', async () => {
    const handler = createOraclePenalizedHandler(mockT, router);

    const result = await handler.handle({ oracle: 'coingecko', penaltyDuration: 1800, reason: 'timeout' });
    assert(!Array.isArray(result.action));
    assert(result.action);

    await result.action.action();

    expect(push).toHaveBeenCalledWith({ name: '/settings/oracle/', hash: `#${SettingsCategoryIds.PRICE_ORACLE}` });
  });
});
