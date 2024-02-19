import { mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { createTestingPinia } from '@pinia/testing';

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    restartBackend: vi.fn(),
    config: vi.fn().mockReturnValue({
      logDirectory: '/Users/home/rotki/logs',
    }),
  }),
}));

vi.mock('@/utils/account-management', () => ({
  getBackendUrl: vi.fn().mockReturnValue({
    sessionOnly: true,
    url: '',
  }),
  deleteBackendUrl: vi.fn(),
}));

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

describe('composables::backend', () => {
  beforeAll(() => {
    const pinia = createTestingPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should use default config', async () => {
    const loaded = vi.fn();
    let backendManagement: ReturnType<typeof useBackendManagement> | null = null;

    mount({
      template: '<div/>',
      setup() {
        backendManagement = useBackendManagement(loaded);
      },
    });

    await nextTick();
    await flushPromises();

    expect(backendManagement).not.toBeNull();
    const { options, defaultLogDirectory, fileConfig } = backendManagement!;

    expect(get(options)).toStrictEqual({
      loglevel: 'debug',
      logDirectory: '/Users/home/rotki/logs',
    });
    expect(get(fileConfig)).toStrictEqual({
      logDirectory: '/Users/home/rotki/logs',
    });

    expect(get(defaultLogDirectory)).toBe('/Users/home/rotki/logs');
    expect(loaded).toHaveBeenCalledOnce();
  });

  it('should get saved data in localStorage', async () => {
    const loaded = vi.fn();
    const savedOptions = {
      loglevel: 'critical',
      maxSizeInMbAllLogs: 10,
      sqliteInstructions: 100,
      maxLogfilesNum: 1000,
    };
    localStorage.setItem(BACKEND_OPTIONS, JSON.stringify(savedOptions));

    let backendManagement: ReturnType<typeof useBackendManagement> | null = null;

    mount({
      template: '<div/>',
      setup() {
        backendManagement = useBackendManagement(loaded);
      },
    });

    await nextTick();
    await flushPromises();

    expect(backendManagement).not.toBeNull();
    const { options } = backendManagement!;

    expect(get(options)).toStrictEqual({
      logDirectory: '/Users/home/rotki/logs',
      loglevel: 'critical',
      maxLogfilesNum: 1000,
      maxSizeInMbAllLogs: 10,
      sqliteInstructions: 100,
    });

    expect(loaded).toHaveBeenCalledOnce();
  });

  it('should save options', async () => {
    const { saveOptions } = useBackendManagement();
    const newOptions = {
      logDirectory: 'new_log_directory',
      dataDirectory: 'new_data_directory',
    };

    await saveOptions(newOptions);

    expect(
      JSON.parse(localStorage.getItem(BACKEND_OPTIONS) || ''),
    ).toStrictEqual(newOptions);

    expect(useInterop().restartBackend).toBeCalledWith(newOptions);
  });

  it('should reset options', async () => {
    const { resetOptions } = useBackendManagement();

    await resetOptions();

    expect(
      JSON.parse(localStorage.getItem(BACKEND_OPTIONS) || ''),
    ).toStrictEqual({});

    expect(useInterop().restartBackend).toBeCalledWith({});
  });

  it('should restart backend session', async () => {
    const { resetSessionBackend } = useBackendManagement();

    await resetSessionBackend();

    expect(useInterop().restartBackend).toBeCalledWith({
      logDirectory: '/Users/home/rotki/logs',
    });
  });

  it('should not restart backend session', async () => {
    vi.mocked(getBackendUrl).mockReturnValue({
      sessionOnly: false,
      url: '',
    });
    const { resetSessionBackend } = useBackendManagement();

    await resetSessionBackend();

    expect(useInterop().restartBackend).not.toBeCalled();
  });

  it('should restart backend if the url is not set', async () => {
    const url = '';
    const { backendChanged } = useBackendManagement();

    await backendChanged(url);

    expect(useInterop().restartBackend).toBeCalled();
    expect(useMainStore().connect).toHaveBeenCalledWith(url);
  });

  it('should not backend if the url is set', async () => {
    const url = 'test_backend_url';
    const { backendChanged } = useBackendManagement();

    await backendChanged(url);

    expect(useInterop().restartBackend).not.toBeCalled();
    expect(useMainStore().connect).toHaveBeenCalledWith(url);
  });

  it('should not do anything on setupBackend, if connected=true', async () => {
    const store = useMainStore();
    store.connected = true;

    const { setupBackend } = useBackendManagement();

    await setupBackend();

    expect(useInterop().restartBackend).not.toBeCalled();
  });

  it('should restart backend, if connected=false and url is not set', async () => {
    const store = useMainStore();
    store.connected = false;
    const { setupBackend } = useBackendManagement();

    await setupBackend();

    expect(useInterop().restartBackend).toBeCalled();
    expect(store.connect).toHaveBeenCalledWith();
  });

  it('should not restart backend, if connected=false and url is set', async () => {
    const store = useMainStore();
    store.connected = false;

    const url = 'test_backend_url';

    vi.mocked(getBackendUrl).mockReturnValue({
      sessionOnly: false,
      url,
    });

    const { setupBackend } = useBackendManagement();

    await setupBackend();

    expect(useInterop().restartBackend).not.toBeCalled();
    expect(store.connect).toHaveBeenCalledWith(url);
  });
});
