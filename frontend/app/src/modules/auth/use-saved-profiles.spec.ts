import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockGetUserProfiles = vi.fn();

vi.mock('@/modules/auth/use-users-api', () => ({
  useUsersApi: vi.fn(() => ({
    getUserProfiles: mockGetUserProfiles,
  })),
}));

describe('modules::auth::use-saved-profiles', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
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
