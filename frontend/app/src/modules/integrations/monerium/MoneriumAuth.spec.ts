import type { OAuthResult } from '@shared/ipc';
import type { useMoneriumOAuth } from './use-monerium-auth';
import { NotificationGroup, Severity } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MoneriumAuth from './MoneriumAuth.vue';

const { mockCompleteOAuth, mockNotify, mockOpenUrl, mockRemoveMatching } = vi.hoisted(() => ({
  mockCompleteOAuth: vi.fn(),
  mockNotify: vi.fn(),
  mockOpenUrl: vi.fn(),
  mockRemoveMatching: vi.fn<(predicate: (notification: { group?: NotificationGroup }) => boolean) => void>(),
}));
let oAuthHandler: ((result: OAuthResult) => Promise<void> | void) | undefined;

vi.mock('@/modules/core/notifications/use-notifications', () => ({
  useNotifications: vi.fn(() => ({
    notify: mockNotify,
    removeMatching: mockRemoveMatching,
  })),
}));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: vi.fn(() => ({
    isPackaged: true,
    openUrl: mockOpenUrl,
  })),
}));

vi.mock('@/modules/shell/app/use-backend-messages', () => ({
  useBackendMessages: vi.fn(() => ({
    registerOAuthCallbackHandler: vi.fn((handler: (result: OAuthResult) => Promise<void> | void) => {
      oAuthHandler = handler;
    }),
    unregisterOAuthCallbackHandler: vi.fn(() => {
      oAuthHandler = undefined;
    }),
  })),
}));

vi.mock('./use-monerium-auth', () => ({
  useMoneriumOAuth: vi.fn(() => createMock<ReturnType<typeof useMoneriumOAuth>>({
    authenticated: computed<boolean>(() => false),
    completeOAuth: mockCompleteOAuth,
    disconnect: vi.fn(),
    status: ref(undefined),
  })),
}));

describe('moneriumAuth', () => {
  let wrapper: VueWrapper<InstanceType<typeof MoneriumAuth>>;

  function createWrapper(): VueWrapper<InstanceType<typeof MoneriumAuth>> {
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(MoneriumAuth, {
      global: {
        plugins: [pinia],
        stubs: {
          ServiceKeyCard: {
            emits: ['confirm'],
            template: '<div><button data-testid="connect" @click="$emit(\'confirm\')" /><slot /></div>',
          },
        },
      },
    });
  }

  beforeEach(() => {
    vi.stubEnv('VITE_ROTKI_WEBSITE_URL', 'https://rotki.com');
    vi.clearAllMocks();
    oAuthHandler = undefined;
    mockCompleteOAuth.mockResolvedValue({ message: 'connected' });
    wrapper = createWrapper();
  });

  afterEach(() => {
    wrapper.unmount();
    vi.unstubAllEnvs();
  });

  it('should group the notification announcing that the browser is opening', async () => {
    await wrapper.find('[data-testid=connect]').trigger('click');
    await nextTick();

    expect(mockOpenUrl).toHaveBeenCalledWith('https://rotki.com/oauth/monerium?mode=app');
    expect(mockNotify).toHaveBeenCalledWith(expect.objectContaining({
      display: true,
      group: NotificationGroup.MONERIUM_AUTH,
      severity: Severity.INFO,
    }));
  });

  it('should raise no notification when the authorization completes', async () => {
    expect(oAuthHandler).toBeDefined();
    await oAuthHandler?.({
      accessToken: 'access',
      refreshToken: 'refresh',
      service: 'monerium',
      success: true,
    });

    // the card reports this inline by flipping to its connected state
    expect(mockCompleteOAuth).toHaveBeenCalledOnce();
    expect(mockNotify).not.toHaveBeenCalled();
  });

  it('should clear the flow notifications when the authorization completes', async () => {
    await oAuthHandler?.({
      accessToken: 'access',
      refreshToken: 'refresh',
      service: 'monerium',
      success: true,
    });

    expect(mockRemoveMatching).toHaveBeenCalledOnce();
    const [predicate] = mockRemoveMatching.mock.calls[0];
    expect(predicate({ group: NotificationGroup.MONERIUM_AUTH })).toBe(true);
    expect(predicate({ group: NotificationGroup.MISSING_API_KEY })).toBe(false);
    expect(predicate({})).toBe(false);
  });

  it('should group the notification for a failed authorization', async () => {
    mockCompleteOAuth.mockRejectedValue(new Error('nope'));

    await oAuthHandler?.({
      accessToken: 'access',
      refreshToken: 'refresh',
      service: 'monerium',
      success: true,
    });

    expect(mockNotify).toHaveBeenCalledWith(expect.objectContaining({
      group: NotificationGroup.MONERIUM_AUTH,
      message: 'nope',
      severity: Severity.ERROR,
    }));
  });
});
