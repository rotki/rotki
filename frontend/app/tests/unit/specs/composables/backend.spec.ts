import { mount } from '@vue/test-utils';
import { useBackendManagement } from '@/composables/backend';

vi.mock('@/composables/electron-interop', () => ({
  useInterop: vi.fn().mockReturnValue({
    isPackaged: true,
    restartBackend: vi.fn(),
    config: vi.fn().mockReturnValue({
      logDirectory: '/Users/home/rotki/logs'
    })
  })
}));

vi.mock('@/utils/account-management', () => ({
  getBackendUrl: vi.fn().mockReturnValue({
    sessionOnly: true,
    url: ''
  }),
  deleteBackendUrl: vi.fn()
}));

vi.mock('@/store/main', () => ({
  useMainStore: vi.fn().mockReturnValue({
    connected: false,
    setConnected: vi.fn(),
    connect: vi.fn()
  })
}));

const BACKEND_OPTIONS = 'BACKEND_OPTIONS';

describe('composables::backend', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('should use default config', async () => {
    const loaded = vi.fn();
    let backendManagement: ReturnType<typeof useBackendManagement> | null =
      null;

    const wrapper = mount({
      setup() {
        backendManagement = useBackendManagement(loaded);
      }
    });

    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(backendManagement).not.toBeNull();
    const { options, defaultLogDirectory, fileConfig } = backendManagement!;

    expect(get(options)).toStrictEqual({
      loglevel: 'debug',
      logDirectory: '/Users/home/rotki/logs'
    });
    expect(get(fileConfig)).toStrictEqual({
      logDirectory: '/Users/home/rotki/logs'
    });

    expect(get(defaultLogDirectory)).toBe('/Users/home/rotki/logs');
    expect(loaded).toHaveBeenCalledOnce();
  });

  test('should get saved data in localStorage', async () => {
    const loaded = vi.fn();
    const savedOptions = {
      loglevel: 'critical',
      maxSizeInMbAllLogs: 10,
      sqliteInstructions: 100,
      maxLogfilesNum: 1000
    };
    localStorage.setItem(BACKEND_OPTIONS, JSON.stringify(savedOptions));

    let backendManagement: ReturnType<typeof useBackendManagement> | null =
      null;

    const wrapper = mount({
      setup() {
        backendManagement = useBackendManagement(loaded);
      }
    });

    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(backendManagement).not.toBeNull();
    const { options } = backendManagement!;

    expect(get(options)).toStrictEqual({
      logDirectory: '/Users/home/rotki/logs',
      loglevel: 'critical',
      maxLogfilesNum: 1000,
      maxSizeInMbAllLogs: 10,
      sqliteInstructions: 100
    });

    expect(loaded).toHaveBeenCalledOnce();
  });

  test('should save options', async () => {
    const { saveOptions } = useBackendManagement();
    const newOptions = {
      logDirectory: 'new_log_directory',
      dataDirectory: 'new_data_directory'
    };

    await saveOptions(newOptions);

    expect(
      JSON.parse(localStorage.getItem(BACKEND_OPTIONS) || '')
    ).toStrictEqual(newOptions);

    expect(useInterop().restartBackend).toBeCalledWith(newOptions);
  });

  test('should reset options', async () => {
    const { resetOptions } = useBackendManagement();

    await resetOptions();

    expect(
      JSON.parse(localStorage.getItem(BACKEND_OPTIONS) || '')
    ).toStrictEqual({});

    expect(useInterop().restartBackend).toBeCalledWith({});
  });

  test('should restart backend session', async () => {
    const { resetSessionBackend } = useBackendManagement();

    await resetSessionBackend();

    expect(useInterop().restartBackend).toBeCalledWith({
      logDirectory: '/Users/home/rotki/logs'
    });
  });

  test('should not restart backend session', async () => {
    vi.mocked(getBackendUrl).mockReturnValue({
      sessionOnly: false,
      url: ''
    });
    const { resetSessionBackend } = useBackendManagement();

    await resetSessionBackend();

    expect(useInterop().restartBackend).not.toBeCalled();
  });

  test('should restart backend if the url is not set', async () => {
    const url = '';
    const { backendChanged } = useBackendManagement();

    await backendChanged(url);

    expect(useInterop().restartBackend).toBeCalled();
    expect(useMainStore().connect).toHaveBeenCalledWith(url);
  });

  test('should not backend if the url is set', async () => {
    const url = 'test_backend_url';
    const { backendChanged } = useBackendManagement();

    await backendChanged(url);

    expect(useInterop().restartBackend).not.toBeCalled();
    expect(useMainStore().connect).toHaveBeenCalledWith(url);
  });

  test('should not do anything on setupBackend, if connected=true', async () => {
    const { connected } = storeToRefs(useMainStore());
    set(connected, true);

    const { setupBackend } = useBackendManagement();

    await setupBackend();

    expect(useInterop().restartBackend).not.toBeCalled();
  });

  test('should restart backend, if connected=false and url is not set', async () => {
    const store = useMainStore();
    const { connected } = storeToRefs(store);
    const { connect } = store;
    set(connected, false);

    const { setupBackend } = useBackendManagement();

    await setupBackend();

    expect(useInterop().restartBackend).toBeCalled();
    expect(connect).toHaveBeenCalledWith();
  });

  test('should not restart backend, if connected=false and url is set', async () => {
    const store = useMainStore();
    const { connected } = storeToRefs(store);
    const { connect } = store;
    set(connected, false);

    const url = 'test_backend_url';

    vi.mocked(getBackendUrl).mockReturnValue({
      sessionOnly: false,
      url
    });

    const { setupBackend } = useBackendManagement();

    await setupBackend();

    expect(useInterop().restartBackend).not.toBeCalled();
    expect(connect).toHaveBeenCalledWith(url);
  });
});
