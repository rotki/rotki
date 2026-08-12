import type { GnosisPaySafeMigration } from '@/modules/integrations/gnosis-pay/types';
import { Blockchain } from '@rotki/common';
import dayjs from 'dayjs';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const WEEK_IN_SECONDS = 7 * 24 * 60 * 60;
const NEW_SAFE = '0xabcdef1234567890abcdef1234567890abcdef12';
const OLD_SAFE = '0x1234567890abcdef1234567890abcdef12345678';

const fetchGnosisPaySafeMigration = vi.fn();
const addAccounts = vi.fn();
const notify = vi.fn();
const showErrorMessage = vi.fn();
const showSuccessMessage = vi.fn();
const updateFrontendSetting = vi.fn();
const getApiKey = vi.fn();
const loadExternalKeys = vi.fn();
const externalKeys = ref<Record<string, unknown> | undefined>({ gnosis_pay: { apiKey: 'gpay-token' } });

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-api', () => ({
  useGnosisPaySiweApi: vi.fn().mockImplementation(() => ({ fetchGnosisPaySafeMigration })),
}));

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn().mockImplementation(() => ({ addAccounts })),
}));

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn().mockImplementation(() => ({ notify, showErrorMessage, showSuccessMessage })),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn().mockImplementation(() => ({ updateFrontendSetting })),
}));

vi.mock('@/modules/settings/api-keys/external/use-external-api-keys', () => ({
  useExternalApiKeys: vi.fn().mockImplementation(() => ({ getApiKey, keys: externalKeys, load: loadExternalKeys })),
}));

vi.mock('@/modules/core/common/logging/logging', () => ({
  logger: { debug: vi.fn(), error: vi.fn(), info: vi.fn(), warn: vi.fn() },
}));

function migration(untracked: GnosisPaySafeMigration['untrackedAddresses']): GnosisPaySafeMigration {
  return { migrationId: 'safe-replacement-2026-06', untrackedAddresses: untracked };
}

async function setup(settings?: Record<string, unknown>): Promise<{
  composable: Awaited<ReturnType<typeof import('./use-gnosis-pay-safe-migration')['useGnosisPaySafeMigration']>>;
}> {
  if (settings) {
    const { useSettingsRepo } = await import('@/modules/settings/settings-repo');
    useSettingsRepo().updateFrontend(settings);
  }
  const { useGnosisPaySafeMigration } = await import('./use-gnosis-pay-safe-migration');
  return { composable: useGnosisPaySafeMigration() };
}

describe('useGnosisPaySafeMigration', () => {
  beforeEach(() => {
    vi.resetModules();
    setActivePinia(createPinia());
    fetchGnosisPaySafeMigration.mockReset();
    // The real `addAccounts` resolves an `AdditionSummary` and does not throw on a failed add, so
    // `undefined` here let the composable claim success for an addition that never happened.
    addAccounts.mockReset().mockResolvedValue({
      added: [{ address: NEW_SAFE, chain: Blockchain.GNOSIS }],
      cancelled: false,
      failed: [],
    });
    notify.mockReset();
    showErrorMessage.mockReset();
    showSuccessMessage.mockReset();
    updateFrontendSetting.mockReset().mockResolvedValue(undefined);
    getApiKey.mockReset().mockReturnValue('gpay-token');
    loadExternalKeys.mockReset().mockResolvedValue(undefined);
    set(externalKeys, { gnosis_pay: { apiKey: 'gpay-token' } });
  });

  it('should expose the first untracked safe after checking', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup();

    await composable.checkMigration();

    expect(get(composable.untrackedSafe)).toEqual({ address: NEW_SAFE, type: 'new' });
    expect(get(composable.hasUntrackedSafe)).toBe(true);
  });

  it('should skip the request entirely when Gnosis Pay is not configured', async () => {
    getApiKey.mockReturnValue('');
    const { composable } = await setup();

    await composable.checkMigration();

    expect(fetchGnosisPaySafeMigration).not.toHaveBeenCalled();
    expect(get(composable.untrackedSafe)).toBeUndefined();
  });

  it('should load the external keys first when they are not loaded yet', async () => {
    set(externalKeys, undefined);
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup();

    await composable.checkMigration();

    expect(loadExternalKeys).toHaveBeenCalled();
    expect(fetchGnosisPaySafeMigration).toHaveBeenCalled();
  });

  it('should clear the untracked safe when the migration has none', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([]));
    const { composable } = await setup();

    await composable.checkMigration();

    expect(get(composable.untrackedSafe)).toBeUndefined();
    expect(get(composable.hasUntrackedSafe)).toBe(false);
  });

  it('should fail silently when the endpoint errors (not configured / not premium)', async () => {
    fetchGnosisPaySafeMigration.mockRejectedValue(new Error('Gnosis Pay credentials are not configured'));
    const { composable } = await setup();

    await expect(composable.checkMigration()).resolves.toBeUndefined();
    expect(get(composable.untrackedSafe)).toBeUndefined();
  });

  it('should add the missing safe to Gnosis Chain and report success', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(addAccounts).toHaveBeenCalledWith(
      Blockchain.GNOSIS,
      { payload: [{ address: NEW_SAFE, label: expect.any(String), tags: null }] },
      { wait: true },
    );
    expect(get(composable.untrackedSafe)).toBeUndefined();
    expect(showSuccessMessage).toHaveBeenCalled();
    expect(showErrorMessage).not.toHaveBeenCalled();
  });

  it('should surface an error and keep the safe when adding fails', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockRejectedValue(new Error('boom'));
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(showErrorMessage).toHaveBeenCalled();
    expect(get(composable.untrackedSafe)).toEqual({ address: OLD_SAFE, type: 'old' });
  });

  // Additions report failure as a value, not a throw. Without reading the summary the Safe was
  // announced as added and the suggestion dismissed while nothing had been stored.
  it('should surface an error and keep the safe when the addition reports a failure', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockResolvedValue({
      added: [],
      cancelled: false,
      failed: [{ account: { address: OLD_SAFE, tags: null }, error: TaskFailed({ message: 'node unreachable' }) }],
    });
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(showSuccessMessage).not.toHaveBeenCalled();
    expect(showErrorMessage).toHaveBeenCalled();
    expect(get(composable.untrackedSafe)).toEqual({ address: OLD_SAFE, type: 'old' });
  });

  it('should keep the safe and stay silent when the addition is cancelled', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockResolvedValue({ added: [], cancelled: true, failed: [] });
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(showSuccessMessage).not.toHaveBeenCalled();
    expect(showErrorMessage).not.toHaveBeenCalled();
    expect(get(composable.untrackedSafe)).toEqual({ address: OLD_SAFE, type: 'old' });
  });

  it('should notify once and record the timestamp when never shown before', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup({ gnosisPaySafeMigrationLastNotified: 0, gnosisPaySafeMigrationNeverNotify: false });

    await composable.checkAndNotify();

    expect(notify).toHaveBeenCalledTimes(1);
    const payload = notify.mock.calls[0][0];
    expect(payload.message).toContain('message_new');
    expect(payload.message).toContain(NEW_SAFE);
    expect(updateFrontendSetting).toHaveBeenCalledWith(
      expect.objectContaining({ gnosisPaySafeMigrationLastNotified: expect.any(Number) }),
    );
  });

  it('should not notify when the user chose never to be reminded', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup({ gnosisPaySafeMigrationNeverNotify: true });

    await composable.checkAndNotify();

    expect(notify).not.toHaveBeenCalled();
  });

  it('should not notify again within a week', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup({ gnosisPaySafeMigrationLastNotified: dayjs().unix() - 10 });

    await composable.checkAndNotify();

    expect(notify).not.toHaveBeenCalled();
  });

  it('should notify again once a week has passed', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    const { composable } = await setup({ gnosisPaySafeMigrationLastNotified: dayjs().unix() - WEEK_IN_SECONDS - 10 });

    await composable.checkAndNotify();

    expect(notify).toHaveBeenCalledTimes(1);
    expect(notify.mock.calls[0][0].message).toContain('message_old');
  });

  it('should wire the notification actions to add and to never-show-again', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { composable } = await setup({ gnosisPaySafeMigrationLastNotified: 0 });

    await composable.checkAndNotify();

    const actions = notify.mock.calls[0][0].action;
    expect(actions).toHaveLength(2);

    await actions[0].action();
    expect(addAccounts).toHaveBeenCalled();

    await actions[1].action();
    expect(updateFrontendSetting).toHaveBeenCalledWith({ gnosisPaySafeMigrationNeverNotify: true });
  });
});
