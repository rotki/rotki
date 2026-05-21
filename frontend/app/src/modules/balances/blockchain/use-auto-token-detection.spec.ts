import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAutoTokenDetection } from '@/modules/balances/blockchain/use-auto-token-detection';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const detectAllTokens = vi.fn();
const updateFrontendSetting = vi.fn();

vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', () => ({
  useTokenDetectionOrchestrator: (): Record<string, ReturnType<typeof vi.fn>> => ({
    detectAllTokens,
    detectTokens: vi.fn(),
    useIsDetecting: vi.fn(),
  }),
}));

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

describe('useAutoTokenDetection', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    detectAllTokens.mockReset().mockResolvedValue(undefined);
    updateFrontendSetting.mockReset().mockResolvedValue({ success: true });
    useFrontendSettingsStore().update({
      autoDetectTokensCooldownHours: 24,
      autoDetectTokensOnLogin: true,
      lastAutoDetectAt: 0,
    });
  });

  it('should run detection when auto-detect is on and cooldown has elapsed', async () => {
    const { maybeDetect } = useAutoTokenDetection();
    await maybeDetect();

    expect(detectAllTokens).toHaveBeenCalledTimes(1);
    expect(updateFrontendSetting).toHaveBeenCalledWith({ lastAutoDetectAt: expect.any(Number) });
  });

  it('should skip detection when auto-detect is disabled', async () => {
    useFrontendSettingsStore().update({ autoDetectTokensOnLogin: false });
    const { maybeDetect } = useAutoTokenDetection();
    await maybeDetect();

    expect(detectAllTokens).not.toHaveBeenCalled();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should skip detection when last run is within the cooldown window', async () => {
    useFrontendSettingsStore().update({
      autoDetectTokensCooldownHours: 24,
      lastAutoDetectAt: Date.now() - 1 * HOUR_MS,
    });
    const { maybeDetect } = useAutoTokenDetection();
    await maybeDetect();

    expect(detectAllTokens).not.toHaveBeenCalled();
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should run detection when the cooldown window has elapsed', async () => {
    useFrontendSettingsStore().update({
      autoDetectTokensCooldownHours: 24,
      lastAutoDetectAt: Date.now() - 25 * HOUR_MS,
    });
    const { maybeDetect } = useAutoTokenDetection();
    await maybeDetect();

    expect(detectAllTokens).toHaveBeenCalledTimes(1);
    expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
  });

  it('should run detection once when called concurrently', async () => {
    let resolve!: () => void;
    detectAllTokens.mockReturnValueOnce(new Promise<void>((r) => {
      resolve = r;
    }));
    const { maybeDetect } = useAutoTokenDetection();

    const first = maybeDetect();
    const second = maybeDetect();
    resolve();
    await Promise.all([first, second]);

    expect(detectAllTokens).toHaveBeenCalledTimes(1);
    expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
  });

  it('should report the skip reason via skipReason()', () => {
    const store = useFrontendSettingsStore();
    const { skipReason } = useAutoTokenDetection();
    expect(skipReason()).toBeNull();

    store.update({ autoDetectTokensOnLogin: false });
    expect(skipReason()).toBe('auto-detect-tokens-on-login disabled');

    store.update({
      autoDetectTokensCooldownHours: 24,
      autoDetectTokensOnLogin: true,
      lastAutoDetectAt: Date.now() - 1 * HOUR_MS,
    });
    expect(skipReason()).toMatch(/^within cooldown \(\d+m remaining\)$/);
  });

  it('should run detection when lastAutoDetectAt is in the future (clock skew)', async () => {
    useFrontendSettingsStore().update({
      autoDetectTokensCooldownHours: 24,
      lastAutoDetectAt: Date.now() + 48 * HOUR_MS,
    });
    const { maybeDetect } = useAutoTokenDetection();
    await maybeDetect();

    expect(detectAllTokens).toHaveBeenCalledTimes(1);
  });

  it('should still update lastAutoDetectAt when detection throws', async () => {
    detectAllTokens.mockRejectedValueOnce(new Error('boom'));
    const { maybeDetect } = useAutoTokenDetection();
    await maybeDetect();

    expect(detectAllTokens).toHaveBeenCalledTimes(1);
    expect(updateFrontendSetting).toHaveBeenCalledWith({ lastAutoDetectAt: expect.any(Number) });
  });
});
