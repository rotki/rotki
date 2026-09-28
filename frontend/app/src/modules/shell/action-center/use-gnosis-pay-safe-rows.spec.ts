import type { EffectScope } from 'vue';
import type { ActionItem } from '@/modules/core/action-center/types';
import type { GnosisPayUntrackedSafe } from '@/modules/integrations/gnosis-pay/types';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { useGnosisPaySafeRows } from '@/modules/shell/action-center/use-gnosis-pay-safe-rows';

const SAFE = '0xabcdef1234567890abcdef1234567890abcdef12';

const untrackedSafe = ref<GnosisPayUntrackedSafe>();
const adding = ref<boolean>(false);
const neverShow = ref<boolean>(false);
const addMissingSafe = vi.fn<() => Promise<void>>();
const checkMigration = vi.fn<() => Promise<void>>();
const updateFrontendSetting = vi.fn<(payload: object) => Promise<{ success: boolean }>>();
const show = vi.fn<(message: { title: string; message: string }, onConfirm: () => Promise<void>) => void>();

vi.mock('@/modules/integrations/gnosis-pay/use-gnosis-pay-safe-migration', () => ({
  useGnosisPaySafeMigration: (): object => ({ addMissingSafe, adding, checkMigration, untrackedSafe }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): Ref<boolean> => neverShow,
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

vi.mock('@/modules/core/common/use-confirm-store', () => ({
  useConfirmStore: (): object => ({ show }),
}));

let scope: EffectScope | undefined;

function safeRows(): ReturnType<typeof useGnosisPaySafeRows> {
  scope = effectScope();
  const result = scope.run(() => useGnosisPaySafeRows());
  assert(result);
  return result;
}

function safeRow(): ActionItem {
  const [row] = get(safeRows().rows);
  assert(row);
  return row;
}

describe('modules/shell/action-center/use-gnosis-pay-safe-rows', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    addMissingSafe.mockResolvedValue();
    updateFrontendSetting.mockResolvedValue({ success: true });
    set(untrackedSafe, { address: SAFE, type: 'new' });
    set(adding, false);
    set(neverShow, false);
  });

  afterEach(() => {
    scope?.stop();
  });

  it('should raise the row while the migration left a Safe untracked, naming it', () => {
    const row = safeRow();

    expect(row.count).toBe(1);
    expect(row.description).toBe(`external_services.gnosispay.safe_migration.missing_new::${SAFE}`);
  });

  it('should describe a previous Safe as the one to add for its history', () => {
    set(untrackedSafe, { address: SAFE, type: 'old' });

    expect(safeRow().description).toBe(`external_services.gnosispay.safe_migration.missing_old::${SAFE}`);
  });

  it('should raise nothing once every Safe is tracked', () => {
    set(untrackedSafe, undefined);

    expect(safeRow().count).toBe(0);
  });

  it('should raise nothing once the user asked not to be shown it again', () => {
    set(neverShow, true);

    expect(safeRow().count).toBe(0);
  });

  it('should add the Safe in place, keeping the center open to show the outcome', () => {
    const { target } = safeRow();
    assert(target.kind === 'run');

    expect(target.closesCenter).toBeUndefined();
    target.run();
    expect(addMissingSafe).toHaveBeenCalledOnce();
  });

  it('should show the row busy while the Safe is being added', () => {
    const { rows } = safeRows();
    set(adding, true);

    expect(get(rows)[0].loading).toBe(true);
  });

  it('should open the external services page when cleared, not the sign-in dialog the service query opens', () => {
    expect(safeRow().checkTarget).toEqual({ kind: 'route', to: { name: '/api-keys/external/' } });
  });

  it('should ask before suppressing, then write the setting that keeps it from being raised', async () => {
    const option = safeRow().options.find(({ id }) => id === 'do-not-show-again');
    assert(option?.target.kind === 'run');
    option.target.run();

    expect(updateFrontendSetting).not.toHaveBeenCalled();
    const [message, onConfirm] = show.mock.calls[0];
    expect(message.title).toBe('action_center.rows.integrations.gnosis_pay_safe_migration.suppress_confirm.title');

    await onConfirm();

    expect(updateFrontendSetting).toHaveBeenCalledWith({ gnosisPaySafeMigrationNeverNotify: true });
  });

  it('should re-read the migration on refresh', async () => {
    await safeRows().refresh();

    expect(checkMigration).toHaveBeenCalledOnce();
  });
});
