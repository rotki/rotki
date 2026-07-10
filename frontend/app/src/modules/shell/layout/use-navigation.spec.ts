import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';

const mockPush = vi.fn();
const mockCurrentRoute = ref<{ name?: string }>({ name: '/' });

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    currentRoute: mockCurrentRoute,
    push: mockPush,
  })),
}));

describe('modules::shell::use-navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockCurrentRoute, { name: '/' });
  });

  describe('navigateToUserLogin', () => {
    it('should push to /user/login with no query', async () => {
      const { navigateToUserLogin } = useAppNavigation();

      await navigateToUserLogin();

      expect(mockPush).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith({ name: '/user/login/' });
    });

    it('should be a no-op when already on the login route', async () => {
      set(mockCurrentRoute, { name: '/user/login/' });

      const { navigateToUserLogin } = useAppNavigation();
      await navigateToUserLogin();

      expect(mockPush).not.toHaveBeenCalled();
    });
  });

  describe('navigateToUserCreation', () => {
    it('should push to /user/create', async () => {
      const { navigateToUserCreation } = useAppNavigation();

      await navigateToUserCreation();

      expect(mockPush).toHaveBeenCalledWith({ name: '/user/create/' });
    });
  });

  describe('navigateToDashboard', () => {
    it('should push to the dashboard route', async () => {
      const { navigateToDashboard } = useAppNavigation();

      await navigateToDashboard();

      expect(mockPush).toHaveBeenCalledWith({ name: '/dashboard/' });
    });
  });
});
