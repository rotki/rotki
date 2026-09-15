import type { FrontendSettingsPayload } from '@/modules/settings/types/frontend-settings';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { getCurrentInstance } from 'vue';
import { useSettingsRepo } from '@/modules/settings/settings-repo';
import { useFrontendSettingsWriter } from '@/modules/settings/use-frontend-settings-writer';

const { mockPatchFrontendSettings } = vi.hoisted(() => ({ mockPatchFrontendSettings: vi.fn() }));

vi.mock('@/modules/settings/api/use-settings-api', () => ({
  useSettingsApi: vi.fn(() => ({ patchFrontendSettings: mockPatchFrontendSettings })),
}));

describe('useFrontendSettingsWriter', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockPatchFrontendSettings.mockReset().mockResolvedValue(undefined);
  });

  it('should be usable outside a component setup', async () => {
    expect(getCurrentInstance()).toBeNull();

    const { updateFrontendSetting } = useFrontendSettingsWriter();
    const status = await updateFrontendSetting({ suppressNoIndexerChains: [] });

    expect(status.success).toBe(true);
  });

  it('should send only the changed keys, not the whole blob', async () => {
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ suppressNoIndexerChains: ['optimism'] });

    expect(mockPatchFrontendSettings).toHaveBeenCalledWith({ suppressNoIndexerChains: ['optimism'] });
  });

  it('should add nothing to the payload, the schema version included', async () => {
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ decimalSeparator: '#' });

    expect(Object.keys(mockPatchFrontendSettings.mock.calls[0][0])).toStrictEqual(['decimalSeparator']);
  });

  it('should apply the patch to the repo once it is persisted', async () => {
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ suppressNoIndexerChains: ['blockscout'] });

    expect(useSettingsRepo().frontend.suppressNoIndexerChains).toStrictEqual(['blockscout']);
  });

  it('should report a failure instead of throwing', async () => {
    mockPatchFrontendSettings.mockRejectedValue(new Error('backend is down'));
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    const status = await updateFrontendSetting({ suppressNoIndexerChains: [] });

    expect(status).toStrictEqual({ message: 'backend is down', success: false });
  });

  it('should not leave the repo updated when the write fails', async () => {
    mockPatchFrontendSettings.mockRejectedValue(new Error('backend is down'));
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await updateFrontendSetting({ suppressNoIndexerChains: ['optimism'] });

    expect(useSettingsRepo().frontend.suppressNoIndexerChains).toStrictEqual([]);
  });

  /**
   * Holds the first write open so the second one is issued while it is still unresolved, and
   * records every patch that reaches the api.
   */
  function captureConcurrentWrites(): { patches: FrontendSettingsPayload[]; release: () => void } {
    const patches: FrontendSettingsPayload[] = [];
    let release = (): void => {};
    const firstInFlight = new Promise<void>((resolve) => {
      release = resolve;
    });
    mockPatchFrontendSettings.mockImplementation(async (payload: FrontendSettingsPayload) => {
      patches.push(payload);
      if (patches.length === 1)
        await firstInFlight;
    });
    return { patches, release };
  }

  it('should not drop a concurrent write of another setting', async () => {
    const { patches, release } = captureConcurrentWrites();

    const { updateFrontendSetting } = useFrontendSettingsWriter();
    const first = updateFrontendSetting({ decimalSeparator: '#' });
    const second = updateFrontendSetting({ thousandSeparator: '@' });
    release();
    await Promise.all([first, second]);

    const repo = useSettingsRepo();
    expect(repo.frontend.decimalSeparator).toBe('#');
    expect(repo.frontend.thousandSeparator).toBe('@');
    expect(patches).toStrictEqual([
      { decimalSeparator: '#' },
      { thousandSeparator: '@' },
    ]);
  });

  it('should serialise writes issued from separate writer instances', async () => {
    const { patches, release } = captureConcurrentWrites();

    const first = useFrontendSettingsWriter().updateFrontendSetting({ decimalSeparator: '#' });
    const second = useFrontendSettingsWriter().updateFrontendSetting({ thousandSeparator: '@' });
    release();
    await Promise.all([first, second]);

    expect(patches).toStrictEqual([
      { decimalSeparator: '#' },
      { thousandSeparator: '@' },
    ]);
  });

  it('should keep writing after a failed write', async () => {
    mockPatchFrontendSettings.mockRejectedValueOnce(new Error('backend is down'));
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    const failed = await updateFrontendSetting({ decimalSeparator: '#' });
    const next = await updateFrontendSetting({ thousandSeparator: '@' });

    expect(failed.success).toBe(false);
    expect(next.success).toBe(true);
  });

  it('should reject an empty payload', async () => {
    const { updateFrontendSetting } = useFrontendSettingsWriter();

    await expect(updateFrontendSetting({})).rejects.toThrow('Payload must be not-empty');
  });
});
