import { afterEach } from 'vitest';
import { type AssetMergePayload, type AssetUpdatePayload } from '@/types/asset';

vi.mock('@/composables/api/assets/index', () => ({
  useAssetsApi: vi.fn().mockReturnValue({
    checkForAssetUpdate: vi.fn().mockResolvedValue(1),
    performUpdate: vi.fn().mockResolvedValue(1),
    mergeAssets: vi.fn().mockResolvedValue(true),
    importCustom: vi.fn().mockResolvedValue({}),
    exportCustom: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/store/tasks', () => ({
  useTaskStore: vi.fn().mockReturnValue({
    awaitTask: vi.fn().mockResolvedValue({})
  })
}));

vi.mock('@/store/notifications/index', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn().mockReturnValue({})
  })
}));

vi.mock('@/composables/electron-interop', () => {
  const mockInterop = {
    appSession: vi.fn(),
    openDirectory: vi.fn()
  };
  return {
    useInterop: vi.fn().mockReturnValue(mockInterop),
    interop: mockInterop
  };
});

describe('store::assets/index', () => {
  setActivePinia(createPinia());
  let store: ReturnType<typeof useAssets>;
  let api: ReturnType<typeof useAssetsApi>;

  beforeEach(() => {
    store = useAssets();
    api = useAssetsApi();
    vi.clearAllMocks();
  });

  describe('checkForUpdate', () => {
    describe('success', () => {
      afterEach(() => {
        expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
        expect(useNotificationsStore().notify).not.toHaveBeenCalled();
      });

      test('update available', async () => {
        const versions = {
          local: 14,
          remote: 16,
          newChanges: 2
        };

        vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
          result: versions,
          meta: { title: '' }
        });

        const result = await store.checkForUpdate();

        expect(result).toEqual({
          updateAvailable: true,
          versions
        });
      });

      test('update not available', async () => {
        const versions = {
          local: 14,
          remote: 14,
          newChanges: 2
        };

        vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
          result: versions,
          meta: { title: '' }
        });

        const result = await store.checkForUpdate();

        expect(result).toEqual({
          updateAvailable: false,
          versions
        });
      });
    });

    test('error', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(
        new Error('failed')
      );

      const result = await store.checkForUpdate();

      expect(api.checkForAssetUpdate).toHaveBeenCalledOnce();
      expect(result).toEqual({
        updateAvailable: false
      });

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('applyUpdates', () => {
    const payload: AssetUpdatePayload = {
      version: 16,
      resolution: {
        ETH: 'local'
      }
    };

    describe('success', () => {
      afterEach(() => {
        expect(api.performUpdate).toHaveBeenCalledOnce();
        expect(useNotificationsStore().notify).not.toHaveBeenCalled();
      });

      test('done', async () => {
        vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
          result: true,
          meta: { title: '' }
        });

        const result = await store.applyUpdates(payload);

        expect(result).toEqual({
          done: true
        });
      });

      test('done', async () => {
        const conflicts = [
          {
            identifier: 'ETH',
            local: {},
            remote: {}
          }
        ];

        vi.mocked(useTaskStore().awaitTask).mockResolvedValue({
          result: conflicts,
          meta: { title: '' }
        });

        const result = await store.applyUpdates(payload);

        expect(result).toEqual({
          done: false,
          conflicts
        });
      });
    });

    test('error', async () => {
      vi.mocked(useTaskStore().awaitTask).mockRejectedValue(
        new Error('failed')
      );

      const result = await store.applyUpdates(payload);

      expect(api.performUpdate).toHaveBeenCalledOnce();
      expect(result).toEqual({
        done: false
      });

      expect(useNotificationsStore().notify).toHaveBeenCalled();
    });
  });

  describe('mergeAssets', () => {
    const payload: AssetMergePayload = {
      sourceIdentifier: 'ETH2',
      targetIdentifier: 'ETH'
    };

    test('success', async () => {
      vi.mocked(api.mergeAssets).mockResolvedValue(true);

      const result = await store.mergeAssets(payload);

      expect(api.mergeAssets).toHaveBeenCalledWith(
        payload.sourceIdentifier,
        payload.targetIdentifier
      );

      expect(result).toEqual({
        success: true
      });
    });

    test('failed', async () => {
      vi.mocked(api.mergeAssets).mockRejectedValue(new Error('failed'));

      const result = await store.mergeAssets(payload);

      expect(api.mergeAssets).toHaveBeenCalledWith(
        payload.sourceIdentifier,
        payload.targetIdentifier
      );

      expect(result).toEqual({
        success: false,
        message: 'failed'
      });
    });
  });

  describe('importCustomAssets', () => {
    const file = new File(['0'], 'test.csv');
    test('success', async () => {
      const result = await store.importCustomAssets(file);

      expect(api.importCustom).toHaveBeenCalledWith(file, false);

      expect(result).toEqual({
        success: true
      });
    });

    test('failed', async () => {
      vi.mocked(api.importCustom).mockRejectedValue(new Error('failed'));

      const result = await store.importCustomAssets(file);

      expect(api.importCustom).toHaveBeenCalledWith(file, false);

      expect(result).toEqual({
        success: false,
        message: 'failed'
      });
    });
  });

  describe('exportCustomAsset', () => {
    const filepath = 'filepath.csv';
    beforeEach(() => {
      vi.mocked(useInterop().openDirectory).mockResolvedValue(filepath);
    });

    test('success', async () => {
      vi.mocked(api.exportCustom).mockResolvedValue({ success: true });
      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(filepath);

      expect(result).toEqual({
        success: true
      });
    });

    test('failed', async () => {
      vi.mocked(api.exportCustom).mockRejectedValue(new Error('failed'));

      const result = await store.exportCustomAssets();

      expect(api.exportCustom).toHaveBeenCalledWith(filepath);

      expect(result).toEqual({
        success: false,
        message: 'failed'
      });
    });
  });
});
