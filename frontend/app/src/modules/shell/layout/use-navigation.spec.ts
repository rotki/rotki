import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAppNavigation } from '@/modules/shell/layout/use-navigation';

const mockPush = vi.fn();
const mockCurrentRoute = ref<{ name?: string; query: Record<string, string> }>({ name: '/', query: {} });

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    currentRoute: mockCurrentRoute,
    push: mockPush,
  })),
}));

describe('modules::shell::use-navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockCurrentRoute, { name: '/', query: {} });
  });

  describe('navigateToUserLogin', () => {
    it('should push to /user/login with no query', async () => {
      const { navigateToUserLogin } = useAppNavigation();

      await navigateToUserLogin();

      expect(mockPush).toHaveBeenCalledTimes(1);
      expect(mockPush).toHaveBeenCalledWith({ name: '/user/login/' });
    });

    it('should be a no-op when already on the login route', async () => {
      set(mockCurrentRoute, { name: '/user/login/', query: {} });

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

  describe('navigateAfterUnlock', () => {
    it('should push to the dashboard when the login carries no redirect', async () => {
      const { navigateAfterUnlock } = useAppNavigation();

      await navigateAfterUnlock();

      expect(mockPush).toHaveBeenCalledWith({ name: '/dashboard/' });
    });

    it('should push to the page the login was redirected from', async () => {
      set(mockCurrentRoute, { name: '/user/login/', query: { redirect: '/history/events?page=2' } });
      const { navigateAfterUnlock } = useAppNavigation();

      await navigateAfterUnlock();

      expect(mockPush).toHaveBeenCalledWith('/history/events?page=2');
    });
  });
});
