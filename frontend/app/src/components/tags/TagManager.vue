<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import RowActions from '@/components/helper/RowActions.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import TagFormDialog from '@/components/tags/TagFormDialog.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useConfirmStore } from '@/store/confirm';
import { useTagStore } from '@/store/session/tags';
import { defaultTag, type Tag } from '@/types/tags';

const { t } = useI18n({ useScope: 'global' });

const tag = ref<Tag | undefined>(undefined);
const editMode = ref<boolean>(false);
const search = ref<string>('');
const originalName = ref<string>('');

const route = useRoute();
const router = useRouter();

const store = useTagStore();
const { deleteTag } = store;
const { tags } = storeToRefs(store);
const { show } = useConfirmStore();

const sort = ref<DataTableSortData<Tag>>({
  column: 'name',
  direction: 'asc',
});

const headers = computed<DataTableColumn<Tag>[]>(() => [
  {
    key: 'name',
    label: t('common.name'),
    sortable: true,
  },
  {
    cellClass: 'w-1/2 !text-sm !text-rui-text-secondary',
    key: 'description',
    label: t('common.description'),
    sortable: true,
  },
  {
    key: 'tagView',
    label: t('tag_creator.tag_view'),
  },
  {
    cellClass: 'w-20',
    key: 'action',
    label: t('common.actions_text'),
    sortable: false,
  },
]);

useRememberTableSorting<Tag>(TableId.TAG_MANAGER, sort, headers);

function editItem(newTag: Tag) {
  set(editMode, true);
  set(originalName, newTag.name);
  set(tag, { ...newTag });
}

function showDeleteConfirmation(selectedTag: Tag) {
  show(
    {
      message: t('tag_manager.confirmation.message', {
        tagToDelete: selectedTag.name,
      }),
      title: t('tag_manager.confirmation.title'),
    },
    () => deleteTag(selectedTag.name),
  );
}

function handleCreateTagClick() {
  set(editMode, false);
  set(originalName, '');
  set(tag, defaultTag());
}

onMounted(async () => {
  const { query } = get(route);
  if (query.add) {
    handleCreateTagClick();
    await router.replace({ query: {} });
  }
});
</script>

<template>
  <TablePageLayout :title="[t('tag_manager.title')]">
    <template #buttons>
      <RuiButton
        color="primary"
        data-cy="add-tags"
        @click="handleCreateTagClick()"
      >
        <template #prepend>
          <RuiIcon name="lu-plus" />
        </template>
        {{ t('tag_manager.create_tag.title') }}
      </RuiButton>
    </template>

    <RuiCard content-class="flex flex-col gap-4">
      <RuiTextField
        v-model="search"
        variant="outlined"
        color="primary"
        dense
        clearable
        prepend-icon="lu-search"
        :label="t('common.actions.search')"
        hide-details
      />
      <RuiDataTable
        v-model:sort="sort"
        dense
        outlined
        :rows="tags"
        row-attr="name"
        :cols="headers"
        :search="search"
      >
        <template #item.tagView="{ row }">
          <TagIcon
            :tag="row"
            small
          />
        </template>
        <template #item.action="{ row }">
          <RowActions
            @edit-click="editItem(row)"
            @delete-click="showDeleteConfirmation(row)"
          />
        </template>
      </RuiDataTable>
    </RuiCard>

    <TagFormDialog
      v-model="tag"
      :edit-mode="editMode"
      :original-name="originalName"
    />
  </TablePageLayout>
</template>
