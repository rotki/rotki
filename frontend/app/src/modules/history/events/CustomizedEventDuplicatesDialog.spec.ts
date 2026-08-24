import type { DuplicateRow } from '@/modules/history/events/use-customized-event-duplicates';
import { createMock } from '@test/utils/create-mock';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, nextTick, type VNode } from 'vue';
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import CustomizedEventDuplicatesDialog from '@/modules/history/events/CustomizedEventDuplicatesDialog.vue';
import DuplicateRowActions from '@/modules/history/events/DuplicateRowActions.vue';
import { DuplicatesTab } from '@/modules/history/events/use-customized-event-duplicates-dialog';

/**
 * The seam: this dialog is wiring. It loads on mount, gives each tab its rows and loading state,
 * shows the actions that belong to the tab being viewed, and routes every click to the composable.
 * What those actions do is covered by `use-customized-event-duplicates-dialog.spec.ts`.
 */

const dialogApi = {
  autoFixLoading: ref<boolean>(false),
  autoFixRows: ref<DuplicateRow[]>([]),
  fixSelected: vi.fn(),
  fixSingle: vi.fn(),
  ignoredLoading: ref<boolean>(false),
  ignoredRows: ref<DuplicateRow[]>([]),
  ignoreSelected: vi.fn(),
  ignoreSingle: vi.fn(),
  initialize: vi.fn(async () => Promise.resolve()),
  manualReviewLoading: ref<boolean>(false),
  manualReviewRows: ref<DuplicateRow[]>([]),
  modelActiveTab: ref<number>(DuplicatesTab.AUTO_FIX),
  modelSelectedAutoFix: ref<string[]>([]),
  modelSelectedIgnored: ref<string[]>([]),
  modelSelectedManualReview: ref<string[]>([]),
  restoreSelected: vi.fn(),
  restoreSingle: vi.fn(),
  showInHistoryEvents: vi.fn(),
};

vi.mock('@/modules/history/events/use-customized-event-duplicates-dialog', async (importOriginal) => {
  const original = await importOriginal<typeof import('@/modules/history/events/use-customized-event-duplicates-dialog')>();
  return {
    DuplicatesTab: original.DuplicatesTab,
    useCustomizedEventDuplicatesDialog: (): typeof dialogApi => dialogApi,
  };
});

const autoFixGroupIds = ref<string[]>(['auto-1']);
const manualReviewGroupIds = ref<string[]>(['manual-1']);
const ignoredGroupIds = ref<string[]>(['ignored-1']);

const duplicatesApi = {
  autoFixCount: computed<number>(() => get(autoFixGroupIds).length),
  autoFixGroupIds,
  fixLoading: ref<boolean>(false),
  ignoredCount: computed<number>(() => get(ignoredGroupIds).length),
  ignoredGroupIds,
  ignoreLoading: ref<boolean>(false),
  manualReviewCount: computed<number>(() => get(manualReviewGroupIds).length),
  manualReviewGroupIds,
};

vi.mock('@/modules/history/events/use-customized-event-duplicates', () => ({
  useCustomizedEventDuplicates: (): typeof duplicatesApi => duplicatesApi,
}));

// RuiDialog teleports; stub it so its contents can be queried.
const RuiDialogStub = defineComponent({
  name: 'RuiDialog',
  props: { modelValue: { default: false, type: Boolean } },
  emits: ['update:modelValue'],
  template: '<div v-if="modelValue"><slot /></div>',
});

/** Renders the actions slot with the first row, which is where the per-row buttons live. */
const listStub = defineComponent({
  name: 'CustomizedEventDuplicatesList',
  props: {
    description: { default: '', type: String },
    loading: { default: false, type: Boolean },
    rows: { default: () => [], type: Array },
    selected: { default: () => [], type: Array },
  },
  emits: ['update:selected', 'show-in-history'],
  setup(props, { slots }): () => VNode {
    return () => h('div', slots.actions?.({ row: props.rows[0] }));
  },
});

function row(groupIdentifier: string): DuplicateRow {
  return {
    entry: createMock<DuplicateRow['entry']>({ groupIdentifier }),
    groupIdentifier,
    location: 'ethereum',
    locationLabel: null,
    timestamp: 1,
    txHash: '0xdead',
  };
}

async function createWrapper(): Promise<VueWrapper<InstanceType<typeof CustomizedEventDuplicatesDialog>>> {
  const wrapper = mount(CustomizedEventDuplicatesDialog, {
    global: {
      stubs: {
        CustomizedEventDuplicatesList: listStub,
        RuiDialog: RuiDialogStub,
      },
    },
    props: { modelValue: true },
  });

  await nextTick();
  return wrapper;
}

describe('customizedEventDuplicatesDialog', () => {
  let wrapper: VueWrapper<InstanceType<typeof CustomizedEventDuplicatesDialog>>;

  /**
   * A tab panel is mounted the first time it is shown and then stays in the tree, so the lists are
   * told apart by the description each one was given rather than by position.
   */
  function list(tab: 'auto_fix' | 'manual_review' | 'non_duplicated'): VueWrapper<InstanceType<typeof listStub>> {
    const found = wrapper.findAllComponents(listStub)
      .find(candidate => candidate.props('description') === `customized_event_duplicates.dialog.${tab}_description`);
    assert(found, `the ${tab} list is not rendered`);
    return found;
  }

  async function showTab(tab: number): Promise<void> {
    set(dialogApi.modelActiveTab, tab);
    await flushPromises();
    await nextTick();
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    set(dialogApi.modelActiveTab, DuplicatesTab.AUTO_FIX);
    set(dialogApi.autoFixRows, [row('auto-1')]);
    set(dialogApi.manualReviewRows, [row('manual-1')]);
    set(dialogApi.ignoredRows, [row('ignored-1')]);
    set(dialogApi.modelSelectedAutoFix, []);
    set(dialogApi.modelSelectedManualReview, []);
    set(dialogApi.modelSelectedIgnored, []);
    set(dialogApi.autoFixLoading, false);
    wrapper = await createWrapper();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  it('should load the duplicates when it opens', () => {
    expect(dialogApi.initialize).toHaveBeenCalledOnce();
  });

  it('should give each tab its own rows and loading state', async () => {
    set(dialogApi.autoFixLoading, true);
    await nextTick();

    expect(list('auto_fix').props('rows')).toBe(get(dialogApi.autoFixRows));
    expect(list('auto_fix').props('loading')).toBe(true);

    await showTab(DuplicatesTab.MANUAL_REVIEW);
    expect(list('manual_review').props('rows')).toBe(get(dialogApi.manualReviewRows));
    expect(list('manual_review').props('loading')).toBe(false);

    await showTab(DuplicatesTab.IGNORED);
    expect(list('non_duplicated').props('rows')).toBe(get(dialogApi.ignoredRows));
  });

  it('should ask to show a tab in history events with that tab groups', async () => {
    list('auto_fix').vm.$emit('show-in-history');
    expect(dialogApi.showInHistoryEvents).toHaveBeenCalledWith(['auto-1'], DuplicateHandlingStatus.AUTO_FIX);

    await showTab(DuplicatesTab.MANUAL_REVIEW);
    list('manual_review').vm.$emit('show-in-history');

    expect(dialogApi.showInHistoryEvents).toHaveBeenCalledWith(['manual-1'], DuplicateHandlingStatus.MANUAL_REVIEW);
  });

  it('should route the per-row actions to the row they belong to', async () => {
    const autoFixActions = list('auto_fix').findComponent(DuplicateRowActions);
    autoFixActions.vm.$emit('fix');
    autoFixActions.vm.$emit('ignore');

    await showTab(DuplicatesTab.IGNORED);
    list('non_duplicated').findComponent(DuplicateRowActions).vm.$emit('restore');

    expect(dialogApi.fixSingle).toHaveBeenCalledWith('auto-1');
    expect(dialogApi.ignoreSingle).toHaveBeenCalledWith('auto-1');
    expect(dialogApi.restoreSingle).toHaveBeenCalledWith('ignored-1');
  });

  it('should keep the bulk actions disabled until something is selected', async () => {
    expect(wrapper.find('[data-testid=fix-selected]').attributes('disabled')).toBeDefined();

    set(dialogApi.modelSelectedAutoFix, ['auto-1']);
    await nextTick();

    expect(wrapper.find('[data-testid=fix-selected]').attributes('disabled')).toBeUndefined();
    await wrapper.find('[data-testid=fix-selected]').trigger('click');
    await wrapper.find('[data-testid=ignore-selected]').trigger('click');

    expect(dialogApi.fixSelected).toHaveBeenCalledOnce();
    expect(dialogApi.ignoreSelected).toHaveBeenCalledOnce();
  });

  it('should show only the actions of the tab being viewed', async () => {
    expect(wrapper.find('[data-testid=fix-selected]').exists()).toBe(true);
    expect(wrapper.find('[data-testid=restore-selected]').exists()).toBe(false);

    set(dialogApi.modelActiveTab, DuplicatesTab.MANUAL_REVIEW);
    await nextTick();

    expect(wrapper.find('[data-testid=fix-selected]').exists()).toBe(false);
    expect(wrapper.find('[data-testid=ignore-selected]').exists()).toBe(true);

    set(dialogApi.modelActiveTab, DuplicatesTab.IGNORED);
    set(dialogApi.modelSelectedIgnored, ['ignored-1']);
    await nextTick();

    expect(wrapper.find('[data-testid=ignore-selected]').exists()).toBe(false);
    await wrapper.find('[data-testid=restore-selected]').trigger('click');

    expect(dialogApi.restoreSelected).toHaveBeenCalledOnce();
  });

  it('should close on the close button', async () => {
    await wrapper.find('[data-testid=close-dialog]').trigger('click');

    expect(wrapper.emitted('update:modelValue')).toEqual([[false]]);
  });
});
