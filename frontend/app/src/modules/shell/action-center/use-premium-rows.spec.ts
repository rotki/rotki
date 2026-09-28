import type { EffectScope } from 'vue';
import { externalLinks } from '@shared/external-links';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ActionItem, ActionUrgency } from '@/modules/core/action-center/types';
import { usePremiumRows } from '@/modules/shell/action-center/use-premium-rows';
import { PremiumInactiveCause, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const { deletePremium, show } = vi.hoisted(() => ({
  deletePremium: vi.fn<() => Promise<{ success: boolean }>>(),
  show: vi.fn<(message: { title: string; message: string }, onConfirm: () => Promise<void>) => void>(),
}));

vi.mock('@/modules/premium/use-premium-operations', () => ({
  usePremiumOperations: (): object => ({ deletePremium }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show }),
}));

let scope: EffectScope | undefined;

function premiumRow(cause: PremiumInactiveCause, reason?: string): ActionItem {
  useRaisedConditionsStore().raise({ cause, kind: RaisedConditionKind.PREMIUM_INACTIVE, reason });
  scope = effectScope();
  const rows = scope.run(() => usePremiumRows());
  assert(rows);
  const [row] = get(rows);
  assert(row);
  return row;
}

describe('modules/shell/action-center/use-premium-rows', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    deletePremium.mockResolvedValue({ success: true });
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should raise nothing while premium works or was never set up', () => {
    scope = effectScope();
    const rows = scope.run(() => usePremiumRows());
    assert(rows);

    expect(get(rows)).toEqual([]);
  });

  it('should lead an expired key to renewing, with the premium settings as an option', () => {
    const row = premiumRow(PremiumInactiveCause.EXPIRED);

    expect(row.target).toEqual({ kind: 'external', url: externalLinks.manageSubscriptions });
    expect(row.urgency).toBe(ActionUrgency.DECISION);
    expect(row.options.map(({ id }) => id)).toEqual(['premium-settings', 'remove-premium-key']);
  });

  it('should explain a device limit in the backend words and lead to the premium settings', () => {
    const row = premiumRow(PremiumInactiveCause.DEVICE_LIMIT, 'All 3 devices are in use');

    expect(row.description).toBe('action_center.rows.integrations.premium_inactive.description_device_limit::All 3 devices are in use');
    expect(row.target).toEqual({ kind: 'route', to: { name: '/api-keys/premium/' } });
    expect(row.urgency).toBe(ActionUrgency.DECISION);
  });

  it('should treat an unreachable server as something rotki retries', () => {
    expect(premiumRow(PremiumInactiveCause.UNREACHABLE).urgency).toBe(ActionUrgency.AUTOMATIC);
  });

  it('should ask before removing the premium key, then remove it', async () => {
    const option = premiumRow(PremiumInactiveCause.EXPIRED).options.find(({ id }) => id === 'remove-premium-key');
    assert(option?.target.kind === 'run');
    expect(option.danger).toBe(true);

    option.target.run();

    expect(deletePremium).not.toHaveBeenCalled();
    const [message, onConfirm] = show.mock.calls[0];
    expect(message.title).toBe('action_center.rows.integrations.premium_inactive.remove_confirm.title');

    await onConfirm();

    expect(deletePremium).toHaveBeenCalledOnce();
  });
});
