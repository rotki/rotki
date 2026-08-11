import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useMainStore } from '@/modules/core/common/use-main-store';
import DockerWarning from './DockerWarning.vue';
import UserHost from './UserHost.vue';
import '@test/i18n';

vi.mock('@/modules/auth/use-auto-login', () => ({
  useAutoLogin: (): object => ({ autolog: false }),
}));

interface Setup {
  docker?: boolean;
  riskAccepted?: boolean;
  sessionAuth?: boolean;
}

describe('userHost', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  function createWrapper({ docker = true, riskAccepted = false, sessionAuth = false }: Setup = {}): VueWrapper {
    vi.stubEnv('VITE_DOCKER', docker ? 'true' : 'false');
    const { connected, sessionAuthEnabled, unauthenticatedApiAccepted } = storeToRefs(useMainStore());
    set(connected, true);
    set(unauthenticatedApiAccepted, riskAccepted);
    set(sessionAuthEnabled, sessionAuth);
    return mount(UserHost, { shallow: true });
  }

  const hasWarning = (wrapper: VueWrapper): boolean => wrapper.findComponent(DockerWarning).exists();

  it('should warn when docker has neither session auth nor an accepted risk', () => {
    expect(hasWarning(createWrapper())).toBe(true);
  });

  it('should not warn when session authentication is configured', () => {
    expect(hasWarning(createWrapper({ sessionAuth: true }))).toBe(false);
  });

  it('should not warn when the risk has been accepted', () => {
    expect(hasWarning(createWrapper({ riskAccepted: true }))).toBe(false);
  });

  it('should not warn outside docker', () => {
    expect(hasWarning(createWrapper({ docker: false }))).toBe(false);
  });
});
