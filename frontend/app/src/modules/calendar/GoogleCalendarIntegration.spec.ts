import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import GoogleCalendarIntegration from '@/modules/calendar/GoogleCalendarIntegration.vue';

/**
 * The seam: this component is wiring. On mount it reads the status and registers the OAuth handler,
 * on unmount it takes that same handler back off. It shows the connected half or the connect half,
 * offers the manual token form only where there is no callback channel, and routes clicks to the
 * composable, which `use-google-calendar-integration.spec.ts` covers.
 */

const { interop } = vi.hoisted(() => ({ interop: { isPackaged: false, openUrl: vi.fn() } }));

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): typeof interop => interop,
}));

const registerOAuthCallbackHandler = vi.fn();
const unregisterOAuthCallbackHandler = vi.fn();

vi.mock('@/modules/shell/app/use-backend-messages', () => ({
  useBackendMessages: (): {
    registerOAuthCallbackHandler: typeof registerOAuthCallbackHandler;
    unregisterOAuthCallbackHandler: typeof unregisterOAuthCallbackHandler;
  } => ({ registerOAuthCallbackHandler, unregisterOAuthCallbackHandler }),
}));

const handleOAuthCallback = vi.fn();

const calendarApi = {
  cancelAuthorization: vi.fn(),
  cancelTokenInput: vi.fn(),
  checkStatus: vi.fn(async () => Promise.resolve()),
  connect: vi.fn(async () => Promise.resolve()),
  connectedUserEmail: ref<string>(''),
  disconnect: vi.fn(async () => Promise.resolve()),
  handleOAuthCallback,
  isAuthorizing: ref<boolean>(false),
  isConnected: ref<boolean>(false),
  isSyncing: ref<boolean>(false),
  modelManualRefreshToken: ref<string>(''),
  modelManualToken: ref<string>(''),
  showTokenInput: ref<boolean>(false),
  submitManualToken: vi.fn(async () => Promise.resolve()),
  sync: vi.fn(async () => Promise.resolve()),
};

vi.mock('@/modules/calendar/use-google-calendar-integration', () => ({
  useGoogleCalendarIntegration: (): typeof calendarApi => calendarApi,
}));

describe('googleCalendarIntegration', () => {
  let wrapper: VueWrapper<InstanceType<typeof GoogleCalendarIntegration>>;

  beforeEach(() => {
    vi.clearAllMocks();
    interop.isPackaged = false;
    set(calendarApi.isConnected, false);
    set(calendarApi.isAuthorizing, false);
    set(calendarApi.isSyncing, false);
    set(calendarApi.showTokenInput, false);
    set(calendarApi.connectedUserEmail, '');
    set(calendarApi.modelManualToken, '');
    set(calendarApi.modelManualRefreshToken, '');
    wrapper = mount(GoogleCalendarIntegration);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should read the status and listen for the callback while it is mounted', () => {
    expect(calendarApi.checkStatus).toHaveBeenCalledOnce();
    expect(registerOAuthCallbackHandler).toHaveBeenCalledWith(handleOAuthCallback);
    expect(unregisterOAuthCallbackHandler).not.toHaveBeenCalled();

    wrapper.unmount();

    // The same handler has to come back off, or the next mount stacks another one on top.
    expect(unregisterOAuthCallbackHandler).toHaveBeenCalledWith(handleOAuthCallback);
  });

  it('should offer to connect while disconnected', async () => {
    expect(wrapper.find('[data-testid=google-calendar-sync]').exists()).toBe(false);

    await wrapper.find('[data-testid=google-calendar-connect]').trigger('click');

    expect(calendarApi.connect).toHaveBeenCalledOnce();
  });

  it('should offer to cancel only while authorizing', async () => {
    expect(wrapper.find('[data-testid=google-calendar-cancel-authorization]').exists()).toBe(false);

    set(calendarApi.isAuthorizing, true);
    await nextTick();

    expect(wrapper.find('[data-testid=google-calendar-connect]').attributes('disabled')).toBeDefined();
    await wrapper.find('[data-testid=google-calendar-cancel-authorization]').trigger('click');

    expect(calendarApi.cancelAuthorization).toHaveBeenCalledOnce();
  });

  describe('the manual token form', () => {
    beforeEach(async () => {
      set(calendarApi.showTokenInput, true);
      await nextTick();
    });

    it('should stay hidden in the packaged app, which gets the tokens back over ipc', async () => {
      wrapper.unmount();
      interop.isPackaged = true;
      wrapper = mount(GoogleCalendarIntegration);
      await nextTick();

      expect(wrapper.find('[data-testid=google-calendar-access-token]').exists()).toBe(false);
    });

    it('should refuse to submit until both tokens are filled in', async () => {
      expect(wrapper.find('[data-testid=google-calendar-submit-token]').attributes('disabled')).toBeDefined();

      set(calendarApi.modelManualToken, 'access');
      await nextTick();
      expect(wrapper.find('[data-testid=google-calendar-submit-token]').attributes('disabled')).toBeDefined();

      set(calendarApi.modelManualRefreshToken, 'refresh');
      await nextTick();
      expect(wrapper.find('[data-testid=google-calendar-submit-token]').attributes('disabled')).toBeUndefined();

      await wrapper.find('[data-testid=google-calendar-submit-token]').trigger('click');
      expect(calendarApi.submitManualToken).toHaveBeenCalledOnce();
    });

    it('should hand the cancel back to the composable', async () => {
      await wrapper.find('[data-testid=google-calendar-cancel-token]').trigger('click');

      expect(calendarApi.cancelTokenInput).toHaveBeenCalledOnce();
    });
  });

  describe('once connected', () => {
    beforeEach(async () => {
      set(calendarApi.isConnected, true);
      await nextTick();
    });

    it('should name the connected account when the backend reported one', async () => {
      expect(wrapper.find('[data-testid=google-calendar-status]').text())
        .toBe('external_services.google_calendar.connected_status');

      set(calendarApi.connectedUserEmail, 'someone@example.com');
      await nextTick();

      expect(wrapper.find('[data-testid=google-calendar-status]').text()).toContain('someone@example.com');
    });

    it('should sync and disconnect through the composable', async () => {
      await wrapper.find('[data-testid=google-calendar-sync]').trigger('click');
      await wrapper.find('[data-testid=google-calendar-disconnect]').trigger('click');

      expect(calendarApi.sync).toHaveBeenCalledOnce();
      expect(calendarApi.disconnect).toHaveBeenCalledOnce();
      expect(wrapper.find('[data-testid=google-calendar-connect]').exists()).toBe(false);
    });

    it('should hold the sync button while a sync is running', async () => {
      set(calendarApi.isSyncing, true);
      await nextTick();

      expect(wrapper.find('[data-testid=google-calendar-sync]').attributes('disabled')).toBeDefined();
    });
  });
});
