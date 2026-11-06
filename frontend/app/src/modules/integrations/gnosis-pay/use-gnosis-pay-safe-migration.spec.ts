import type { AdditionSummary } from '@/modules/accounts/use-account-addition-service';
import type { GnosisPaySafeMigration } from '@/modules/integrations/gnosis-pay/types';
import { Blockchain } from '@rotki/common';
import { logoutThenLogin, sessionRequest } from '@test/utils/realistic-logout';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { hasLiveSession } from '@/modules/core/session/session-lifecycle';
import { TaskFailed } from '@/modules/core/tasks/task-result';

const NEW_SAFE = '0xabcdef1234567890abcdef1234567890abcdef12';
const OLD_SAFE = '0x1234567890abcdef1234567890abcdef12345678';

const fetchGnosisPaySafeMigration = vi.fn();
const addAccounts = vi.fn();
const notifyError = vi.fn<(title: string, message: string) => void>();
const notifyInfo = vi.fn<(title: string, message: string) => void>();
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
  useNotifications: vi.fn().mockImplementation(() => ({ notifyError, notifyInfo })),
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

async function setup(): Promise<{
  composable: Awaited<ReturnType<typeof import('./use-gnosis-pay-safe-migration')['useGnosisPaySafeMigration']>>;
}> {
  const { useGnosisPaySafeMigration } = await import('./use-gnosis-pay-safe-migration');
  return { composable: useGnosisPaySafeMigration() };
}

describe('useGnosisPaySafeMigration', () => {
  beforeEach(() => {
    vi.resetModules();
    setActivePinia(createPinia());
    fetchGnosisPaySafeMigration.mockReset();
    addAccounts.mockReset().mockResolvedValue({
      added: [{ address: NEW_SAFE, chain: Blockchain.GNOSIS }],
      cancelled: false,
      failed: [],
    });
    notifyError.mockReset();
    notifyInfo.mockReset();
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

  it('should add the missing safe to Gnosis Chain and report success with a toast', async () => {
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
    expect(notifyInfo).toHaveBeenCalledExactlyOnceWith('external_services.gnosispay.safe_migration.title', expect.stringContaining('add_success'));
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should toast a failed add from the action center, which has nowhere to name it, and keep the safe', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockRejectedValue(new Error('boom'));
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(notifyError).toHaveBeenCalledExactlyOnceWith('external_services.gnosispay.safe_migration.add_error', 'boom');
    expect(get(composable.addFailure)).toBeUndefined();
    expect(get(composable.untrackedSafe)).toEqual({ address: OLD_SAFE, type: 'old' });
  });

  it('should keep a failed add from the card for its notice, without a toast', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockRejectedValue(new Error('boom'));
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe({ inline: true });

    expect(get(composable.addFailure)).toBe('boom');
    expect(notifyError).not.toHaveBeenCalled();
  });

  it('should drop the kept failure when the next add starts', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockRejectedValueOnce(new Error('boom'));
    addAccounts.mockResolvedValueOnce({ added: [], cancelled: true, failed: [] });
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe({ inline: true });
    await composable.addMissingSafe({ inline: true });

    expect(get(composable.addFailure)).toBeUndefined();
  });

  it('should surface an error and keep the safe when the addition reports failure as a value', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockResolvedValue({
      added: [],
      cancelled: false,
      failed: [{ account: { address: OLD_SAFE, tags: null }, error: TaskFailed({ message: 'node unreachable' }) }],
    });
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(notifyInfo).not.toHaveBeenCalled();
    expect(notifyError).toHaveBeenCalled();
    expect(get(composable.untrackedSafe)).toEqual({ address: OLD_SAFE, type: 'old' });
  });

  it('should keep the safe and stay silent when the addition is cancelled', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: OLD_SAFE, type: 'old' }]));
    addAccounts.mockResolvedValue({ added: [], cancelled: true, failed: [] });
    const { composable } = await setup();
    await composable.checkMigration();

    await composable.addMissingSafe();

    expect(notifyInfo).not.toHaveBeenCalled();
    expect(notifyError).not.toHaveBeenCalled();
    expect(get(composable.untrackedSafe)).toEqual({ address: OLD_SAFE, type: 'old' });
  });

  it('should mark itself adding only while the addition runs', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    let resolve: (summary: AdditionSummary) => void = () => {};
    addAccounts.mockReturnValue(new Promise<AdditionSummary>((settle) => {
      resolve = settle;
    }));
    const { composable } = await setup();
    await composable.checkMigration();

    const adding = composable.addMissingSafe();

    expect(get(composable.adding)).toBe(true);

    resolve({ added: [{ address: NEW_SAFE, chain: Blockchain.GNOSIS }], cancelled: false, failed: [], skipped: 0 });
    await adding;

    expect(get(composable.adding)).toBe(false);
  });

  it('should not toast in the next session when an addition was in flight across a realistic logout', async () => {
    const toastedWithASession: boolean[] = [];
    notifyError.mockImplementation(() => toastedWithASession.push(hasLiveSession()));
    notifyInfo.mockImplementation(() => toastedWithASession.push(hasLiveSession()));
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    addAccounts.mockReturnValue(sessionRequest<AdditionSummary>().promise);
    const { composable } = await setup();
    await composable.checkMigration();

    const adding = composable.addMissingSafe();
    await logoutThenLogin();
    await adding;

    expect(toastedWithASession).not.toContain(true);
    expect(get(composable.adding)).toBe(false);
  });

  it('should forget the untracked safe when the user logs out', async () => {
    fetchGnosisPaySafeMigration.mockResolvedValue(migration([{ address: NEW_SAFE, type: 'new' }]));
    const { useSessionAuthStore } = await import('@/modules/auth/use-session-auth-store');
    const store = useSessionAuthStore();
    store.logged = true;
    const { composable } = await setup();
    await composable.checkMigration();

    store.logged = false;
    await nextTick();

    expect(get(composable.untrackedSafe)).toBeUndefined();
  });
});
