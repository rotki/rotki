import type { Router } from 'vue-router';
import type { OraclePenalizedData } from '@/modules/core/messaging/types';
import { assert, type Notification, NotificationGroup, Priority, Severity } from '@rotki/common';
import { mockT } from '@test/i18n';
import { createMock } from '@test/utils/create-mock';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createOraclePenalizedHandler } from '@/modules/core/messaging/handlers/oracle-penalized';
import { LIVE_DELIVERY, type MessageDelivery } from '@/modules/core/messaging/interfaces';
import { SettingsCategoryIds } from '@/modules/settings/setting-highlight-ids';

const push = vi.fn<Router['push']>();
const router = createMock<Router>({ push });

const PENALTY_SECONDS = 1800;

async function notificationFor(data: OraclePenalizedData, delivery: MessageDelivery = LIVE_DELIVERY): Promise<Notification> {
  const result = await createOraclePenalizedHandler(mockT, router).handle(data, delivery);
  assert(result);
  return result;
}

describe('createOraclePenalizedHandler', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should build a warning that names the oracle and explains it stopped answering', async () => {
    const result = await notificationFor({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });

    expect(result.severity).toBe(Severity.WARNING);
    expect(result.priority).toBe(Priority.HIGH);
    expect(result.display).toBeUndefined();
    expect(result.message).toContain('message_timeout');
    expect(result.message).not.toContain('message_errors');
  });

  it('should explain repeated failures differently from a silent host', async () => {
    const result = await notificationFor({ oracle: 'defillama', penaltyDuration: PENALTY_SECONDS, reason: 'errors' });

    expect(result.message).toContain('message_errors');
    expect(result.message).not.toContain('message_timeout');
  });

  it('should give each oracle its own group so two penalized oracles do not collapse into one', async () => {
    const coingecko = await notificationFor({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });
    const defillama = await notificationFor({ oracle: 'defillama', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });

    expect(coingecko.group).toBe(`${NotificationGroup.ORACLE_PENALIZED}:coingecko`);
    expect(coingecko.group).not.toBe(defillama.group);
  });

  it('should route to the price oracle settings when the action is clicked', async () => {
    const result = await notificationFor({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' });
    assert(!Array.isArray(result.action));
    assert(result.action);

    await result.action.action();

    expect(push).toHaveBeenCalledWith({ name: '/settings/oracle/', hash: `#${SettingsCategoryIds.PRICE_ORACLE}` });
  });

  it('should skip a held penalty that had already run out when it was read', async () => {
    const lastSent = new Date(Date.now() - (PENALTY_SECONDS + 60) * 1000);

    const result = await createOraclePenalizedHandler(mockT, router)
      .handle({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' }, { count: 1, lastSent });

    expect(result).toBeNull();
  });

  it('should show a held penalty that is still running, with how many times it was sent', async () => {
    const lastSent = new Date(Date.now() - 60 * 1000);

    const result = await notificationFor({ oracle: 'coingecko', penaltyDuration: PENALTY_SECONDS, reason: 'timeout' }, { count: 3, lastSent });

    expect(result.message).toMatch(/^notification_messages\.repeated::3, notification_messages\.oracle_penalized\.message_timeout/);
  });
});
