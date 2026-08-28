import type { ResolutionCallbacks } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflict-resolution';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InternalTxConflictsContent from '@/modules/history/internal-tx-conflicts/InternalTxConflictsContent.vue';
import {
  type InternalTxConflict,
  InternalTxConflictActions,
  InternalTxConflictStatuses,
  RedecodeReasons,
  RepullReasons,
} from '@/modules/history/internal-tx-conflicts/types';

const conflictsApi = {
  conflicts: ref<InternalTxConflict[]>([]),
  failedCount: ref<number>(0),
  fetchConflicts: vi.fn(async () => Promise.resolve()),
  fetchCounts: vi.fn(async () => Promise.resolve()),
  filters: ref({}),
  loading: ref<boolean>(false),
  pagination: ref({ limit: 10, page: 1, total: 0 }),
  pendingCount: ref<number>(0),
  setFilter: vi.fn(),
  sort: ref([]),
};

const selectionApi = {
  areAllSelected: vi.fn(() => false),
  clearSelection: vi.fn(),
  isSelected: vi.fn(() => false),
  selectedConflicts: ref<InternalTxConflict[]>([]),
  selectedCount: ref<number>(0),
  toggleAllOnPage: vi.fn(),
  toggleSelection: vi.fn(),
};

const resolutionApi = {
  cancelResolution: vi.fn(),
  isResolving: vi.fn(() => false),
  progress: ref({ isRunning: false }),
  resolveMany: vi.fn<(conflicts: InternalTxConflict[], callbacks: ResolutionCallbacks) => Promise<void>>(
    async () => Promise.resolve(),
  ),
  resolveOne: vi.fn<(conflict: InternalTxConflict, callbacks: ResolutionCallbacks) => Promise<void>>(
    async () => Promise.resolve(),
  ),
};

vi.mock('@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts', () => ({
  useInternalTxConflicts: (): typeof conflictsApi => conflictsApi,
}));

vi.mock('@/modules/history/internal-tx-conflicts/use-internal-tx-conflict-selection', () => ({
  useInternalTxConflictSelection: (): typeof selectionApi => selectionApi,
}));

vi.mock('@/modules/history/internal-tx-conflicts/use-internal-tx-conflict-resolution', () => ({
  useInternalTxConflictResolution: (): typeof resolutionApi => resolutionApi,
}));

vi.mock('@/modules/history/internal-tx-conflicts/use-internal-tx-conflict-fields', () => ({
  useInternalTxConflictFields: (): unknown[] => [],
}));

const stubs = {
  CopyButton: true,
  DateDisplay: true,
  HashLink: true,
  InternalTxConflictRowActions: true,
  LocationIcon: true,
  PillFilterBar: true,
  ScrollableDialogContent: { template: '<div><slot /></div>' },
};

const wrappers: VueWrapper[] = [];

function conflict(overrides: Partial<InternalTxConflict> = {}): InternalTxConflict {
  return {
    action: InternalTxConflictActions.REPULL,
    chain: 'ethereum',
    groupIdentifier: null,
    lastError: null,
    lastRetryTs: null,
    redecodeReason: null,
    repullReason: null,
    timestamp: 1700000000,
    txHash: '0xdead',
    ...overrides,
  };
}

async function mountContent(props: Record<string, unknown> = {}): Promise<VueWrapper> {
  const wrapper = mount(InternalTxConflictsContent, {
    global: { provide: libraryDefaults, stubs },
    props,
  });
  wrappers.push(wrapper);
  await flushPromises();
  return wrapper;
}

function columnKeys(wrapper: VueWrapper): string[] {
  return wrapper.findComponent({ name: 'RuiDataTable' }).props('cols').map((col: { key: string }) => col.key);
}

describe('modules/history/internal-tx-conflicts/InternalTxConflictsContent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(conflictsApi.conflicts, []);
    set(selectionApi.selectedConflicts, []);
    set(selectionApi.selectedCount, 0);
    set(resolutionApi.progress, { isRunning: false });
  });

  afterEach(() => {
    while (wrappers.length > 0)
      wrappers.pop()?.unmount();
  });

  describe('what it does on mount', () => {
    it('should load both the rows and the counts', async () => {
      await mountContent();

      expect(conflictsApi.fetchConflicts).toHaveBeenCalledOnce();
      expect(conflictsApi.fetchCounts).toHaveBeenCalledOnce();
    });

    it('should resolve nothing by itself', async () => {
      await mountContent();

      expect(resolutionApi.resolveOne).not.toHaveBeenCalled();
      expect(resolutionApi.resolveMany).not.toHaveBeenCalled();
    });
  });

  describe('switching tabs', () => {
    it('should clear the selection, so rows picked on one tab cannot be resolved from another', async () => {
      const wrapper = await mountContent();

      await wrapper.findComponent({ name: 'RuiTabs' }).vm.$emit('update:model-value', 1);
      await flushPromises();

      expect(selectionApi.clearSelection).toHaveBeenCalledOnce();
    });

    it.each([
      [1, InternalTxConflictStatuses.FAILED],
      [2, InternalTxConflictStatuses.FIXED],
    ])('should filter to the status behind tab %s', async (tab, status) => {
      const wrapper = await mountContent();

      await wrapper.findComponent({ name: 'RuiTabs' }).vm.$emit('update:model-value', tab);
      await flushPromises();

      expect(conflictsApi.setFilter).toHaveBeenLastCalledWith(status);
    });

    it('should filter back to pending on returning to the first tab', async () => {
      const wrapper = await mountContent();
      const tabs = wrapper.findComponent({ name: 'RuiTabs' });

      await tabs.vm.$emit('update:model-value', 2);
      await flushPromises();
      await tabs.vm.$emit('update:model-value', 0);
      await flushPromises();

      expect(conflictsApi.setFilter).toHaveBeenLastCalledWith(InternalTxConflictStatuses.PENDING);
    });
  });

  describe('resolving the selection', () => {
    it('should send exactly the selected conflicts, not the whole page', async () => {
      const picked = conflict({ txHash: '0xpicked' });
      set(conflictsApi.conflicts, [picked, conflict({ txHash: '0xother' })]);
      set(selectionApi.selectedConflicts, [picked]);
      set(selectionApi.selectedCount, 1);
      const wrapper = await mountContent();

      await wrapper.find('[data-testid="resolve-selected"]').trigger('click');
      await flushPromises();

      expect(resolutionApi.resolveMany).toHaveBeenCalledOnce();
      expect(resolutionApi.resolveMany.mock.calls[0][0]).toEqual([picked]);
    });

    it('should refresh the rows and counts once resolution completes', async () => {
      set(selectionApi.selectedConflicts, [conflict()]);
      set(selectionApi.selectedCount, 1);
      const wrapper = await mountContent();
      conflictsApi.fetchConflicts.mockClear();
      conflictsApi.fetchCounts.mockClear();

      await wrapper.find('[data-testid="resolve-selected"]').trigger('click');
      await resolutionApi.resolveMany.mock.calls[0][1].onComplete();

      expect(conflictsApi.fetchConflicts).toHaveBeenCalledOnce();
      expect(conflictsApi.fetchCounts).toHaveBeenCalledOnce();
    });
  });

  describe('the columns it shows', () => {
    it('should drop the diagnostic columns when compact, where there is no room', async () => {
      const wrapper = await mountContent({ compact: true });

      expect(columnKeys(wrapper)).toEqual(['selection', 'chain', 'txHash', 'timestamp', 'actions']);
    });

    it('should show the reason and last error at full width', async () => {
      const wrapper = await mountContent();

      expect(columnKeys(wrapper)).toContain('reason');
      expect(columnKeys(wrapper)).toContain('lastError');
      expect(columnKeys(wrapper)).toContain('lastRetryTs');
    });
  });

  describe('the reason it shows per row', () => {
    it('should prefer the repull reason when a row carries both', async () => {
      set(conflictsApi.conflicts, [conflict({
        redecodeReason: RedecodeReasons.MIXED_ZERO_GAS,
        repullReason: RepullReasons.ALL_ZERO_GAS,
      })]);

      const wrapper = await mountContent();

      expect(wrapper.text()).toContain('internal_tx_conflicts.reasons.all_zero_gas');
      expect(wrapper.text()).not.toContain('internal_tx_conflicts.reasons.mixed_zero_gas');
    });

    it('should fall back to the redecode reason', async () => {
      set(conflictsApi.conflicts, [conflict({ redecodeReason: RedecodeReasons.DUPLICATE_EXACT_ROWS })]);

      const wrapper = await mountContent();

      expect(wrapper.text()).toContain('internal_tx_conflicts.reasons.duplicate_exact_rows');
    });

    it('should show a dash when a row names no reason at all', async () => {
      set(conflictsApi.conflicts, [conflict()]);

      const wrapper = await mountContent();

      expect(wrapper.text()).toContain('—');
    });
  });
});
