import { beforeEach, describe, expect, it, vi } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { usePrivacyMode } from './use-privacy';

const privacyMode = ref<PrivacyMode>(PrivacyMode.NORMAL);
const updateFrontendSetting = vi.fn();

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn((key: string) => (key === 'privacyMode' ? privacyMode : ref(undefined))),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): object => ({ updateFrontendSetting }),
}));

describe('usePrivacyMode', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(privacyMode, PrivacyMode.NORMAL);
  });

  it.each([
    [PrivacyMode.NORMAL, 'lu-eye'],
    [PrivacyMode.SEMI_PRIVATE, 'lu-eye-off'],
    [PrivacyMode.PRIVATE, 'lu-eye-closed'],
  ])('should map privacy mode %s to icon %s', (mode, icon) => {
    set(privacyMode, mode);
    const { privacyModeIcon } = usePrivacyMode();
    expect(get(privacyModeIcon)).toBe(icon);
  });

  it('should persist the requested mode on change', async () => {
    const { changePrivacyMode } = usePrivacyMode();
    await changePrivacyMode(PrivacyMode.PRIVATE);
    expect(updateFrontendSetting).toHaveBeenCalledWith({ privacyMode: PrivacyMode.PRIVATE });
  });

  it('should cycle to the next mode on toggle', async () => {
    set(privacyMode, PrivacyMode.NORMAL);
    const { togglePrivacyMode } = usePrivacyMode();
    await togglePrivacyMode();
    expect(updateFrontendSetting).toHaveBeenCalledWith({ privacyMode: PrivacyMode.SEMI_PRIVATE });
  });

  it('should wrap around from the last mode back to normal', async () => {
    set(privacyMode, PrivacyMode.PRIVATE);
    const { togglePrivacyMode } = usePrivacyMode();
    await togglePrivacyMode();
    expect(updateFrontendSetting).toHaveBeenCalledWith({ privacyMode: PrivacyMode.NORMAL });
  });
});
