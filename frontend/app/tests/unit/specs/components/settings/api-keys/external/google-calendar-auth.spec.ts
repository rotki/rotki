import GoogleCalendarAuth from '@/components/settings/api-keys/external/GoogleCalendarAuth.vue';
import { useGoogleCalendarApi } from '@/composables/api/settings/google-calendar';
import { useInterop } from '@/composables/electron-interop';
import { useNotificationsStore } from '@/store/notifications';
import { Severity } from '@rotki/common';
import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

// Mock dependencies
vi.mock('@/composables/api/settings/google-calendar');
vi.mock('@/composables/electron-interop');
vi.mock('@/store/notifications');

describe('googleCalendarAuth.vue', () => {
  let mockGoogleCalendarApi: any;
  let mockInterop: any;
  let mockNotificationsStore: any;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Setup mock implementations
    mockGoogleCalendarApi = {
      getStatus: vi.fn().mockResolvedValue({ authenticated: false }),
      startAuth: vi.fn().mockResolvedValue({ auth_url: 'https://accounts.google.com/auth' }),
      completeAuth: vi.fn().mockResolvedValue({ success: true }),
      syncCalendar: vi.fn().mockResolvedValue({
        total_events: 5,
        events_created: 3,
        events_updated: 2,
      }),
      disconnect: vi.fn().mockResolvedValue({ success: true }),
    };

    mockInterop = {
      openUrl: vi.fn().mockResolvedValue(undefined),
    };

    mockNotificationsStore = {
      notify: vi.fn(),
    };

    // Mock return values
    vi.mocked(useGoogleCalendarApi).mockReturnValue(mockGoogleCalendarApi);
    vi.mocked(useInterop).mockReturnValue(mockInterop);
    vi.mocked(useNotificationsStore).mockReturnValue(mockNotificationsStore);
  });

  it('renders correctly when not connected', async () => {
    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    await flushPromises();

    // Check that connect button is shown
    expect(wrapper.find('[data-test="connect-button"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="disconnect-button"]').exists()).toBe(false);
  });

  it('renders correctly when connected', async () => {
    mockGoogleCalendarApi.getStatus.mockResolvedValue({ authenticated: true });

    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    await flushPromises();

    // Check that disconnect button is shown
    expect(wrapper.find('[data-test="connect-button"]').exists()).toBe(false);
    expect(wrapper.find('[data-test="disconnect-button"]').exists()).toBe(true);
    expect(wrapper.find('[data-test="sync-button"]').exists()).toBe(true);
  });

  it('starts OAuth flow correctly', async () => {
    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    await flushPromises();

    // Set credentials
    await wrapper.find('[data-test="client-id-input"]').setValue('test-client-id');
    await wrapper.find('[data-test="client-secret-input"]').setValue('test-client-secret');

    // Click connect button
    await wrapper.find('[data-test="connect-button"]').trigger('click');
    await flushPromises();

    // Check that API was called correctly
    expect(mockGoogleCalendarApi.startAuth).toHaveBeenCalledWith('test-client-id', 'test-client-secret');

    // Check that browser was opened with delay
    await vi.advanceTimersByTime(100);
    expect(mockInterop.openUrl).toHaveBeenCalledWith('https://accounts.google.com/auth');

    // Check that auth dialog is shown
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-test="auth-dialog"]').exists()).toBe(true);
  });

  it('completes OAuth flow correctly', async () => {
    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    // Simulate starting OAuth flow
    await wrapper.find('[data-test="connect-button"]').trigger('click');
    await wrapper.vm.$nextTick();

    // Enter auth code
    await wrapper.find('[data-test="auth-code-input"]').setValue('test-auth-code');

    // Complete authentication
    await wrapper.find('[data-test="complete-auth-button"]').trigger('click');
    await flushPromises();

    // Check API call
    expect(mockGoogleCalendarApi.completeAuth).toHaveBeenCalledWith('test-auth-code');

    // Check success notification
    expect(mockNotificationsStore.notify).toHaveBeenCalledWith({
      display: true,
      message: expect.any(String),
      severity: Severity.INFO,
      title: expect.any(String),
    });

    // Check dialog closed
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-test="auth-dialog"]').exists()).toBe(false);
  });

  it('handles sync correctly', async () => {
    mockGoogleCalendarApi.getStatus.mockResolvedValue({ authenticated: true });

    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    await flushPromises();

    // Click sync button
    await wrapper.find('[data-test="sync-button"]').trigger('click');
    await flushPromises();

    // Check API call
    expect(mockGoogleCalendarApi.syncCalendar).toHaveBeenCalled();

    // Check success notification with sync results
    expect(mockNotificationsStore.notify).toHaveBeenCalledWith({
      display: true,
      message: expect.stringMatching(/3.*2.*5|5.*2.*3/),
      severity: Severity.INFO,
      title: expect.any(String),
    });
  });

  it('handles disconnect correctly', async () => {
    mockGoogleCalendarApi.getStatus.mockResolvedValue({ authenticated: true });

    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    await flushPromises();

    // Click disconnect button
    await wrapper.find('[data-test="disconnect-button"]').trigger('click');
    await flushPromises();

    // Check API call
    expect(mockGoogleCalendarApi.disconnect).toHaveBeenCalled();

    // Check success notification
    expect(mockNotificationsStore.notify).toHaveBeenCalledWith({
      display: true,
      message: expect.any(String),
      severity: Severity.INFO,
      title: expect.any(String),
    });
  });

  it('shows error when credentials are missing', async () => {
    const wrapper = mount(GoogleCalendarAuth, {
      global: {
        stubs: {
          ServiceKeyCard: true,
          RuiButton: true,
          RuiTextField: true,
          RuiDialog: true,
          RuiCard: true,
        },
      },
    });

    await flushPromises();

    // Click connect without entering credentials
    await wrapper.find('[data-test="connect-button"]').trigger('click');
    await flushPromises();

    // Check that API was not called
    expect(mockGoogleCalendarApi.startAuth).not.toHaveBeenCalled();

    // Check error notification
    expect(mockNotificationsStore.notify).toHaveBeenCalledWith({
      display: true,
      message: expect.any(String),
      severity: Severity.ERROR,
      title: expect.any(String),
    });
  });
});
