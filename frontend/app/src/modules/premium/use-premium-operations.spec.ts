import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { usePremiumOperations } from '@/modules/premium/use-premium-operations';

const { spies } = vi.hoisted(() => ({
  spies: {
    setPremiumCredentials: vi.fn<(username: string, apiKey: string, apiSecret: string) => Promise<boolean>>(),
    deletePremiumCredentials: vi.fn<() => Promise<boolean>>(),
    fetchCapabilities: vi.fn<() => Promise<void>>().mockResolvedValue(undefined),
  },
}));

vi.mock('@/modules/premium/use-premium-credentials-api', () => ({
  usePremiumCredentialsApi: (): object => ({
    deletePremiumCredentials: spies.deletePremiumCredentials,
    setPremiumCredentials: spies.setPremiumCredentials,
  }),
}));

vi.mock('@/modules/premium/use-fetch-premium-capabilities', () => ({
  useFetchPremiumCapabilities: (): object => ({
    fetchCapabilities: spies.fetchCapabilities,
  }),
}));

describe('use-premium-operations', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('setup', () => {
    const payload = { apiKey: 'k', apiSecret: 's', username: 'me' };

    it('should refresh capabilities after a successful setup', async () => {
      spies.setPremiumCredentials.mockResolvedValueOnce(true);
      const { setup } = usePremiumOperations();

      const result = await setup(payload);

      expect(result.success).toBe(true);
      expect(spies.setPremiumCredentials).toHaveBeenCalledWith('me', 'k', 's');
      expect(spies.fetchCapabilities).toHaveBeenCalledTimes(1);
    });

    it('should not refresh capabilities when the API reports failure', async () => {
      spies.setPremiumCredentials.mockResolvedValueOnce(false);
      const { setup } = usePremiumOperations();

      const result = await setup(payload);

      expect(result.success).toBe(false);
      expect(spies.fetchCapabilities).not.toHaveBeenCalled();
    });

    it('should not refresh capabilities when setup throws', async () => {
      spies.setPremiumCredentials.mockRejectedValueOnce(new Error('boom'));
      const { setup } = usePremiumOperations();

      const result = await setup(payload);

      expect(result.success).toBe(false);
      expect(spies.fetchCapabilities).not.toHaveBeenCalled();
    });
  });
});
