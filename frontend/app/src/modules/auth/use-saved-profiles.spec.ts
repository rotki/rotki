import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockGetUserProfiles = vi.fn();
const mockSavedUsername = ref<string>('');

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: vi.fn(() => ({
    getUserProfiles: mockGetUserProfiles,
  })),
}));

vi.mock('@/modules/auth/use-remember-settings', () => ({
  useRememberSettings: vi.fn(() => ({
    savedRememberPassword: ref<string | null>(null),
    savedRememberUsername: ref<string | null>(null),
    savedUsername: mockSavedUsername,
  })),
}));

describe('modules::auth::use-saved-profiles', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    set(mockSavedUsername, '');
  });

  it('should expose an empty list before loadProfiles is called', async () => {
    const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
    const { hasProfiles, savedUsernames } = useSavedProfiles();

    expect(get(savedUsernames)).toEqual([]);
    expect(get(hasProfiles)).toBe(false);
  });

  it('should populate savedUsernames and hasProfiles after loadProfiles resolves', async () => {
    mockGetUserProfiles.mockResolvedValue(['alice', 'bob']);

    const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
    const { hasProfiles, loadProfiles, savedUsernames } = useSavedProfiles();

    await loadProfiles();

    expect(get(savedUsernames)).toEqual(['alice', 'bob']);
    expect(get(hasProfiles)).toBe(true);
  });

  it('should report hasProfiles=false when the backend returns no profiles', async () => {
    mockGetUserProfiles.mockResolvedValue([]);

    const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
    const { hasProfiles, loadProfiles, savedUsernames } = useSavedProfiles();

    await loadProfiles();

    expect(get(savedUsernames)).toEqual([]);
    expect(get(hasProfiles)).toBe(false);
  });

  describe('resolveStoredUsername', () => {
    it('should return an empty string when no username is stored', async () => {
      mockGetUserProfiles.mockResolvedValue(['alice']);
      set(mockSavedUsername, '');

      const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
      const { loadProfiles, resolveStoredUsername } = useSavedProfiles();
      await loadProfiles();

      expect(resolveStoredUsername()).toBe('');
      expect(get(mockSavedUsername)).toBe('');
    });

    it('should return the stored username when it exists in the loaded profiles', async () => {
      mockGetUserProfiles.mockResolvedValue(['alice', 'bob']);
      set(mockSavedUsername, 'bob');

      const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
      const { loadProfiles, resolveStoredUsername } = useSavedProfiles();
      await loadProfiles();

      expect(resolveStoredUsername()).toBe('bob');
      expect(get(mockSavedUsername)).toBe('bob');
    });

    it('should clear the persisted username and return empty when the stored profile is missing', async () => {
      mockGetUserProfiles.mockResolvedValue(['alice']);
      set(mockSavedUsername, 'ghost');

      const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
      const { loadProfiles, resolveStoredUsername } = useSavedProfiles();
      await loadProfiles();

      expect(resolveStoredUsername()).toBe('');
      expect(get(mockSavedUsername)).toBe('');
    });
  });

  it('should share state between consumers (createSharedComposable)', async () => {
    mockGetUserProfiles.mockResolvedValue(['alice']);

    const { useSavedProfiles } = await import('@/modules/auth/use-saved-profiles');
    const first = useSavedProfiles();
    const second = useSavedProfiles();

    await first.loadProfiles();

    expect(get(second.savedUsernames)).toEqual(['alice']);
    expect(get(second.hasProfiles)).toBe(true);
    expect(mockGetUserProfiles).toHaveBeenCalledTimes(1);
  });
});
