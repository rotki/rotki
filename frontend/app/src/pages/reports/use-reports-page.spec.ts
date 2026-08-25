import type { VueWrapper } from '@vue/test-utils';
import { withSetup } from '@test/utils/with-setup';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type ComputedRef } from 'vue';
import { useReportsPage } from './use-reports-page';

interface RouteState {
  name: string;
  query: Record<string, string>;
}

const { exportData, generate, importData, onResetUploader, pushMock, replaceMock, routeState } = vi.hoisted(() => {
  const routeState: RouteState = { name: '/reports/', query: {} };
  return {
    exportData: vi.fn(async (): Promise<void> => {}),
    generate: vi.fn(async (): Promise<void> => {}),
    importData: vi.fn(async (): Promise<void> => {}),
    onResetUploader: vi.fn(),
    // `router.push` resolves; a mock returning undefined would break the `startPromise` wrapper.
    pushMock: vi.fn(async (): Promise<void> => {}),
    replaceMock: vi.fn(async (): Promise<void> => {}),
    routeState,
  };
});

vi.mock('vue-router', () => ({
  useRoute: (): ComputedRef<RouteState> => computed(() => ({ name: routeState.name, query: routeState.query })),
  useRouter: (): { push: typeof pushMock; replace: typeof replaceMock } => ({ push: pushMock, replace: replaceMock }),
}));

vi.mock('@/pages/reports/use-reports-page-actions', async () => {
  const { shallowRef } = await import('vue');
  return {
    useReportsPageActions: (): {
      exportData: typeof exportData;
      generate: typeof generate;
      importData: typeof importData;
      importDataLoading: ReturnType<typeof shallowRef<boolean>>;
    } => ({ exportData, generate, importData, importDataLoading: shallowRef(false) }),
  };
});

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): { getPath: () => undefined } => ({ getPath: () => undefined }),
}));

vi.mock('@/modules/task-center/use-task-center', async () => {
  const { computed: computedFn } = await import('vue');
  return {
    useTaskCenter: (): { useIsActive: () => ComputedRef<boolean> } => ({
      useIsActive: (): ComputedRef<boolean> => computedFn(() => false),
    }),
  };
});

describe('pages/reports/useReportsPage', () => {
  // The composable registers an onMounted hook, so a harness left mounted would answer a later test.
  const mounted: VueWrapper[] = [];

  function setup(): ReturnType<typeof useReportsPage> {
    const { result, wrapper } = withSetup(() => useReportsPage({ onResetUploader }));
    mounted.push(wrapper);
    return result;
  }

  beforeEach(() => {
    vi.clearAllMocks();
    routeState.name = '/reports/';
    routeState.query = {};
  });

  afterEach(() => {
    while (mounted.length > 0)
      mounted.pop()?.unmount();
  });

  describe('the regenerate query written by reports/[id]', () => {
    it('should clear the query before generating, so a reload does not run twice', async () => {
      routeState.query = { end: '456', regenerate: 'true', start: '123' };

      setup();
      await flushPromises();

      expect(replaceMock).toHaveBeenCalledWith({ query: {} });
      expect(generate).toHaveBeenCalledWith({ end: 456, start: 123 });
      expect(replaceMock.mock.invocationCallOrder[0]).toBeLessThan(generate.mock.invocationCallOrder[0]);
    });

    it('should do nothing without the regenerate flag, even with a period present', async () => {
      routeState.query = { end: '456', start: '123' };

      setup();
      await flushPromises();

      expect(generate).not.toHaveBeenCalled();
      expect(replaceMock).not.toHaveBeenCalled();
    });

    it('should do nothing when the period is incomplete', async () => {
      routeState.query = { regenerate: 'true', start: '123' };

      setup();
      await flushPromises();

      expect(generate).not.toHaveBeenCalled();
    });
  });

  describe('navigating to a generated report', () => {
    it('should ask reports/[id] to open the actionable panel', async () => {
      const { navigateToReport } = setup();
      await flushPromises();

      navigateToReport(42);

      expect(pushMock).toHaveBeenCalledWith({
        name: '/reports/[id]',
        params: { id: '42' },
        query: { openReportActionable: 'true' },
      });
    });

    it('should not navigate once the user has left the reports list', async () => {
      routeState.name = '/settings/general';

      const { navigateToReport } = setup();
      await flushPromises();

      navigateToReport(42);

      expect(pushMock).not.toHaveBeenCalled();
    });
  });

  describe('completing a debug-data import', () => {
    it('should shut the dialog and drop the held file', async () => {
      const { handleImportComplete, modelImportDataDialog, modelReportDebugData } = setup();
      await flushPromises();

      set(modelImportDataDialog, true);
      set(modelReportDebugData, new File(['{}'], 'debug.json'));

      await handleImportComplete();

      expect(importData).toHaveBeenCalledTimes(1);
      expect(get(modelImportDataDialog)).toBe(false);
      expect(get(modelReportDebugData)).toBeUndefined();
      expect(onResetUploader).toHaveBeenCalledTimes(1);
    });

    it('should import before clearing, so the file is still there when it is read', async () => {
      const { handleImportComplete, modelReportDebugData } = setup();
      await flushPromises();

      set(modelReportDebugData, new File(['{}'], 'debug.json'));
      importData.mockImplementationOnce(async () => {
        expect(get(modelReportDebugData)).toBeDefined();
      });

      await handleImportComplete();

      expect(importData).toHaveBeenCalledTimes(1);
    });
  });

  it('should expose the generation actions untouched', async () => {
    const { exportData: exposedExport, generate: exposedGenerate } = setup();
    await flushPromises();

    expect(exposedExport).toBe(exportData);
    expect(exposedGenerate).toBe(generate);
  });
});
