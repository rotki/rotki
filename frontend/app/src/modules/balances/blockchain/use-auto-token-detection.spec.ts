import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAutoTokenDetection } from '@/modules/balances/blockchain/use-auto-token-detection';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

const updateFrontendSetting = vi.fn();

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): Record<string, ReturnType<typeof vi.fn>> => ({
    applyFrontendSettingLocal: vi.fn(),
    enableModule: vi.fn(),
    setKrakenAccountType: vi.fn(),
    update: vi.fn(),
    updateFrontendSetting,
  }),
}));

const HOUR_MS = 60 * 60 * 1000;

/**
 * Stands in for the pass this composable wraps.
 *
 * @remarks
 * Nothing here detects anything, so what these tests pin is the gate and the cooldown bookkeeping:
 * which value `pass` is handed, and whether the sweep is recorded.
 */
function spyPass(): ReturnType<typeof vi.fn<(detect: boolean) => Promise<void>>> {
  return vi.fn<(detect: boolean) => Promise<void>>(async () => {});
}

describe('useAutoTokenDetection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    updateFrontendSetting.mockReset().mockResolvedValue({ success: true });
    useSettingsRepo().updateFrontend({
      autoDetectTokensCooldownHours: 24,
      autoDetectTokensOnLogin: true,
      lastAutoDetectAt: 0,
    });
  });

  it('should ask for detection when auto-detect is on and cooldown has elapsed', async () => {
    const pass = spyPass();
    await useAutoTokenDetection().withDetection(pass);

    expect(pass).toHaveBeenCalledWith(true);
    expect(updateFrontendSetting).toHaveBeenCalledWith({ lastAutoDetectAt: expect.any(Number) });
  });

  /**
   * The pass still runs — the refresh must happen either way. Only its `detect` argument
   * changes, which is the whole point of threading the flag through rather than skipping the call.
   */
  it('should still run the pass, without detection, when auto-detect is disabled', async () => {
    useSettingsRepo().updateFrontend({ autoDetectTokensOnLogin: false });
    const pass = spyPass();
    await useAutoTokenDetection().withDetection(pass);

    expect(pass).toHaveBeenCalledWith(false);
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should not ask for detection within the cooldown window', async () => {
    useSettingsRepo().updateFrontend({
      autoDetectTokensCooldownHours: 24,
      lastAutoDetectAt: Date.now() - 1 * HOUR_MS,
    });
    const pass = spyPass();
    await useAutoTokenDetection().withDetection(pass);

    expect(pass).toHaveBeenCalledWith(false);
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should ask for detection once the cooldown window has elapsed', async () => {
    useSettingsRepo().updateFrontend({
      autoDetectTokensCooldownHours: 24,
      lastAutoDetectAt: Date.now() - 25 * HOUR_MS,
    });
    const pass = spyPass();
    await useAutoTokenDetection().withDetection(pass);

    expect(pass).toHaveBeenCalledWith(true);
    expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
  });

  it('should ask for detection only once when called concurrently', async () => {
    let release!: () => void;
    // Only the detecting pass blocks, so the second call is free to observe the in-flight sweep.
    const blocked = new Promise<void>((resolve) => {
      release = resolve;
    });
    const pass = vi.fn<(detect: boolean) => Promise<void>>(async (detect) => {
      if (detect)
        await blocked;
    });
    const { withDetection } = useAutoTokenDetection();

    const first = withDetection(pass);
    await withDetection(pass);
    release();
    await first;

    // Both passes run — the second is a refresh too — but only the first was told to detect.
    expect(pass).toHaveBeenCalledTimes(2);
    expect(pass.mock.calls.filter(([detect]) => detect)).toHaveLength(1);
    expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
  });

  it('should report the skip reason via skipReason()', () => {
    const store = useSettingsRepo();
    const { skipReason } = useAutoTokenDetection();
    expect(skipReason()).toBeNull();

    store.updateFrontend({ autoDetectTokensOnLogin: false });
    expect(skipReason()).toBe('auto-detect-tokens-on-login disabled');

    store.updateFrontend({
      autoDetectTokensCooldownHours: 24,
      autoDetectTokensOnLogin: true,
      lastAutoDetectAt: Date.now() - 1 * HOUR_MS,
    });
    expect(skipReason()).toMatch(/^within cooldown \(\d+m remaining\)$/);
  });

  it('should ask for detection when lastAutoDetectAt is in the future (clock skew)', async () => {
    useSettingsRepo().updateFrontend({
      autoDetectTokensCooldownHours: 24,
      lastAutoDetectAt: Date.now() + 48 * HOUR_MS,
    });
    const pass = spyPass();
    await useAutoTokenDetection().withDetection(pass);

    expect(pass).toHaveBeenCalledWith(true);
  });

  /** So a persistently broken chain cannot trigger a sweep on every single login. */
  it('should still record the sweep when the pass throws', async () => {
    const pass = vi.fn<(detect: boolean) => Promise<void>>(async () => {
      throw new Error('boom');
    });

    await expect(useAutoTokenDetection().withDetection(pass)).rejects.toThrow('boom');

    expect(updateFrontendSetting).toHaveBeenCalledWith({ lastAutoDetectAt: expect.any(Number) });
  });
});
