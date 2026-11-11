import type { EffectScope } from 'vue';
import { externalLinks } from '@shared/external-links';
import { flushPromises } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ActionItem, ActionUrgency } from '@/modules/core/action-center/types';
import { usePremiumRows } from '@/modules/shell/action-center/use-premium-rows';
import { PremiumInactiveCause, RaisedConditionKind, useRaisedConditionsStore } from '@/modules/shell/action-center/use-raised-conditions-store';

const { deletePremium, notifyError } = vi.hoisted(() => ({
  deletePremium: vi.fn<() => Promise<{ success: true } | { message: string; success: false }>>(),
  notifyError: vi.fn<(title: string, message: string) => void>(),
}));

vi.mock('@/modules/premium/use-premium-operations', () => ({
  usePremiumOperations: (): object => ({ deletePremium }),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: (): object => ({ notifyError }),
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

  it('should offer managing the premium devices only for a device limit', () => {
    const option = premiumRow(PremiumInactiveCause.DEVICE_LIMIT, 'All 3 devices are in use').options.find(({ id }) => id === 'premium-manage-devices');

    expect(option?.target).toEqual({ kind: 'external', url: externalLinks.premiumDevices });
    expect(premiumRow(PremiumInactiveCause.EXPIRED).options.map(({ id }) => id)).not.toContain('premium-manage-devices');
  });

  it('should treat an unreachable server as something rotki retries', () => {
    expect(premiumRow(PremiumInactiveCause.UNREACHABLE).urgency).toBe(ActionUrgency.AUTOMATIC);
  });

  it('should have the row ask before removing the premium key, then remove it', () => {
    const option = premiumRow(PremiumInactiveCause.EXPIRED).options.find(({ id }) => id === 'remove-premium-key');
    assert(option?.target.kind === 'run');
    expect(option.danger).toBe(true);
    expect(option.confirm?.title).toBe('action_center.rows.integrations.premium_inactive.remove_confirm.title');

    option.target.run();

    expect(deletePremium).toHaveBeenCalledOnce();
  });

  it('should toast a failed removal, the question having closed before it ran', async () => {
    deletePremium.mockResolvedValue({ message: 'server refused', success: false });
    const option = premiumRow(PremiumInactiveCause.EXPIRED).options.find(({ id }) => id === 'remove-premium-key');
    assert(option?.target.kind === 'run');
    option.target.run();

    await flushPromises();

    expect(notifyError).toHaveBeenCalledExactlyOnceWith('premium_settings.error.removing_failed', 'server refused');
  });
});
