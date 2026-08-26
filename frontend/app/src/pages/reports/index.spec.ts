import type { useReportsPage } from '@/pages/reports/use-reports-page';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, type Ref, shallowRef } from 'vue';
import ReportGenerator from '@/modules/reports/ReportGenerator.vue';
import ErrorScreen from '@/modules/shell/components/error/ErrorScreen.vue';
import ProgressScreen from '@/modules/shell/components/ProgressScreen.vue';
import ReportsIndexPage from '@/pages/reports/index.vue';

interface PageState {
  isRunning: boolean;
  /** Filled in by the mocked composable on every mount; see the mock below. */
  modelReportDebugData?: Ref<File | undefined>;
}

const { clearError, exportData, generate, handleImportComplete, pageState, storeState } = vi.hoisted(() => {
  const pageState: PageState = { isRunning: false };
  return {
    clearError: vi.fn(),
    exportData: vi.fn(async (): Promise<void> => {}),
    generate: vi.fn(async (): Promise<void> => {}),
    handleImportComplete: vi.fn(async (): Promise<void> => {}),
    pageState,
    storeState: { error: '', message: '', processingState: '', progress: '' },
  };
});

/**
 * The page is a seam over `useReportsPage`, so the composable is mocked and the assertions are
 * about which screen shows and what each child is handed.
 */
vi.mock('@/pages/reports/use-reports-page', async () => {
  const { computed: computedFn, shallowRef: shallowRefFn } = await import('vue');
  return {
    useReportsPage: (): ReturnType<typeof useReportsPage> => {
      // Published back to the test so it can put a file in the uploader; the import button stays
      // disabled without one, and a click on a disabled button is silently dropped.
      pageState.modelReportDebugData = shallowRefFn<File | undefined>(undefined);
      return {
        exportData,
        generate,
        handleImportComplete,
        importDataLoading: computedFn(() => false),
        isRunning: computedFn(() => pageState.isRunning),
        modelImportDataDialog: shallowRefFn(false),
        modelReportDebugData: pageState.modelReportDebugData,
        navigateToReport: vi.fn(),
      };
    },
  };
});

vi.mock('@/modules/reports/use-reports-store', () => ({
  useReportsStore: (): {
    clearError: typeof clearError;
    processingState: string;
    progress: string;
    reportError: ReturnType<typeof shallowRef<{ error: string; message: string }>>;
  } => ({
    clearError,
    processingState: storeState.processingState,
    progress: storeState.progress,
    reportError: shallowRef({ error: storeState.error, message: storeState.message }),
  }),
}));

vi.mock('pinia', async importOriginal => ({
  ...(await importOriginal<typeof import('pinia')>()),
  storeToRefs: (store: Record<string, unknown>): Record<string, unknown> => store,
}));

describe('pages/reports/index', () => {
  let wrapper: VueWrapper<InstanceType<typeof ReportsIndexPage>>;

  /** The debug-data model the mocked composable published on the last mount. */
  function debugDataModel(): Ref<File | undefined> {
    const model = pageState.modelReportDebugData;
    if (!model)
      throw new Error('mount the page before reaching for its debug-data model');

    return model;
  }

  /**
   * The generator and the table are toggled with `v-show`, so they stay in the tree and only the
   * inline style changes. VTU's `isVisible()` reports true for both states on a wrapper that was
   * never attached to the document, so the style is read directly.
   */
  function isHidden(testId: string): boolean {
    return wrapper.find(`[data-testid=${testId}]`).attributes('style')?.includes('display: none') ?? false;
  }

  function mountPage(): VueWrapper<InstanceType<typeof ReportsIndexPage>> {
    return mount(ReportsIndexPage, {
      global: {
        plugins: [createPinia()],
        provide: libraryDefaults,
        stubs: {
          ErrorScreen: { props: ['message', 'error', 'title', 'subtitle'], template: '<div data-testid="error-stub"><slot name="bottom" /></div>' },
          FileUpload: { props: ['modelValue', 'source', 'fileFilter'], template: '<div data-testid="upload-stub" />' },
          ProgressScreen: { props: ['progress'], template: '<div data-testid="progress-stub"><slot name="message" /><slot /></div>' },
          ReportGenerator: { emits: ['generate', 'export-data', 'import-data'], template: '<div data-testid="generator-stub" />' },
          ReportsTable: { template: '<div data-testid="table-stub" />' },
          // RuiDialog teleports its contents; a pass-through keeps them in the tree.
          RuiDialog: { props: ['modelValue', 'maxWidth'], template: '<div><slot /></div>' },
        },
      },
    });
  }

  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    pageState.isRunning = false;
    storeState.error = '';
    storeState.message = '';
    storeState.processingState = '';
    storeState.progress = '';
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('should show the generator and the table while idle', () => {
    wrapper = mountPage();

    expect(isHidden('generator-stub')).toBe(false);
    expect(isHidden('table-stub')).toBe(false);
    expect(wrapper.find('[data-testid=progress-stub]').exists()).toBe(false);
  });

  it('should replace them with the progress screen while a report is running', () => {
    pageState.isRunning = true;
    storeState.progress = '40';
    storeState.processingState = 'crunching';

    wrapper = mountPage();

    expect(wrapper.find('[data-testid=progress-stub]').exists()).toBe(true);
    expect(isHidden('generator-stub')).toBe(true);
    expect(isHidden('table-stub')).toBe(true);
  });

  it('should hand the progress and the processing state to the progress screen', () => {
    pageState.isRunning = true;
    storeState.progress = '40';
    storeState.processingState = 'crunching';

    wrapper = mountPage();

    expect(wrapper.findComponent(ProgressScreen).props('progress')).toBe('40');
    expect(wrapper.find('[data-testid=progress-stub]').text()).toContain('crunching');
  });

  describe('when the last report errored', () => {
    beforeEach(() => {
      storeState.message = 'it broke';
      storeState.error = 'stack';
    });

    it('should show the error screen instead of the generator', () => {
      wrapper = mountPage();

      expect(wrapper.findComponent(ErrorScreen).props('message')).toBe('it broke');
      expect(wrapper.findComponent(ErrorScreen).props('error')).toBe('stack');
      expect(isHidden('generator-stub')).toBe(true);
    });

    it('should clear the error from the close button', async () => {
      wrapper = mountPage();

      await wrapper.find('[data-testid=clear-error]').trigger('click');

      expect(clearError).toHaveBeenCalledTimes(1);
    });

    it('should stay on the progress screen when a run is in flight, error or not', () => {
      pageState.isRunning = true;

      wrapper = mountPage();

      expect(wrapper.findComponent(ErrorScreen).exists()).toBe(false);
      expect(wrapper.find('[data-testid=progress-stub]').exists()).toBe(true);
    });
  });

  it('should forward the generator events with their payloads', () => {
    wrapper = mountPage();
    const generator = wrapper.findComponent(ReportGenerator);

    generator.vm.$emit('generate', { end: 2, start: 1 });
    expect(generate).toHaveBeenCalledWith({ end: 2, start: 1 });

    generator.vm.$emit('export-data', { end: 2, start: 1 });
    expect(exportData).toHaveBeenCalledWith({ end: 2, start: 1 });
  });

  it('should keep the import disabled until a file is chosen', async () => {
    wrapper = mountPage();

    const confirm = wrapper.find('[data-testid=confirm-import]');
    expect(confirm.attributes('disabled')).toBeDefined();

    set(debugDataModel(), new File(['{}'], 'debug.json'));
    await nextTick();

    expect(confirm.attributes('disabled')).toBeUndefined();
  });

  it('should run the import from the dialog confirm button', async () => {
    wrapper = mountPage();
    set(debugDataModel(), new File(['{}'], 'debug.json'));
    await nextTick();

    await wrapper.find('[data-testid=confirm-import]').trigger('click');

    expect(handleImportComplete).toHaveBeenCalledTimes(1);
  });
});
