import type { Tag } from '@/modules/tags/tags';
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import TagManager from '@/modules/tags/TagManager.vue';

const { deleteTag } = vi.hoisted(() => ({
  deleteTag: vi.fn<(name: string) => Promise<void>>(async () => {}),
}));

vi.mock('@/modules/tags/use-tag-operations', () => ({
  useTagOperations: (): { deleteTag: typeof deleteTag } => ({ deleteTag }),
}));

vi.mock('@/modules/core/common/use-add-query', () => ({
  useAddQuery: (): { consumeAddQuery: () => Promise<boolean> } => ({ consumeAddQuery: async () => false }),
}));

vi.mock('@/modules/core/table/use-remember-table-sorting', async importOriginal => ({
  ...await importOriginal<typeof import('@/modules/core/table/use-remember-table-sorting')>(),
  useRememberTableSorting: (): void => {},
}));

/** Renders only the actions cell of each row, which is where a row's delete is wired. */
const TableStub = defineComponent({
  props: ['rows'],
  template: `<div>
    <template v-for="row in rows" :key="row.name">
      <slot name="item.action" :row="row" />
    </template>
  </div>`,
});

const RowActionsStub = defineComponent({
  emits: ['edit-click', 'delete-click'],
  props: ['deleteConfirm'],
  template: '<div />',
});

const tag: Tag = { backgroundColor: 'ffffff', description: '', foregroundColor: '000000', name: 'savings' };

function createWrapper(): VueWrapper<any> {
  return mount(TagManager, {
    global: {
      stubs: {
        RowActions: RowActionsStub,
        RuiDataTable: TableStub,
        TableFrame: { template: '<div><slot /></div>' },
        TablePageLayout: { template: '<div><slot /></div>' },
        TagFormDialog: true,
      },
    },
  });
}

function actions(wrapper: VueWrapper<any>): VueWrapper<any> {
  return wrapper.findComponent(RowActionsStub);
}

describe('tagManager', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    const { allTags } = storeToRefs(useSessionMetadataStore());
    set(allTags, { savings: tag });
  });

  it('should have a tag\'s delete button ask first, saying it also unassigns the tag', () => {
    const wrapper = createWrapper();

    expect(actions(wrapper).props('deleteConfirm')).toEqual({
      message: 'tag_manager.confirmation.message::savings',
      title: 'tag_manager.confirmation.title',
    });
  });

  it('should delete the tag once the delete is confirmed', async () => {
    const wrapper = createWrapper();

    actions(wrapper).vm.$emit('delete-click');
    await flushPromises();

    expect(deleteTag).toHaveBeenCalledWith('savings');
    expect(wrapper.find('[data-testid=tag-manager-delete-error]').exists()).toBe(false);
  });

  it('should name a failed delete above the table, without a retry', async () => {
    deleteTag.mockRejectedValueOnce(new Error('tag is locked'));
    const wrapper = createWrapper();

    actions(wrapper).vm.$emit('delete-click');
    await flushPromises();

    const strip = wrapper.find('[data-testid=tag-manager-delete-error]');
    expect(strip.text()).toContain('actions.session.tag_delete.error.title');
    expect(strip.text()).toContain('tag is locked');
    expect(strip.find('[data-testid=failure-strip-retry]').exists()).toBe(false);
  });
});
