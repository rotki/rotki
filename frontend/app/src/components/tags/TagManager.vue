<script setup lang="ts">
import { type Tag, defaultTag } from '@/types/tags';
import type { DataTableColumn } from '@rotki/ui-library';

const store = useTagStore();
const { deleteTag } = store;
const { tags } = storeToRefs(store);
const { show } = useConfirmStore();

const tag = ref<Tag | undefined>(undefined);
const editMode = ref<boolean>(false);
const search = ref<string>('');

const { t } = useI18n();

const headers = computed<DataTableColumn<Tag>[]>(() => [
  {
    label: t('common.name'),
    key: 'name',
  },
  {
    label: t('common.description'),
    key: 'description',
    cellClass: 'w-3/5 !text-sm !text-rui-text-secondary',
  },
  {
    label: t('tag_creator.tag_view'),
    key: 'tagView',
  },
  {
    label: t('common.actions_text'),
    key: 'action',
    cellClass: 'w-20',
    sortable: false,
  },
]);

function editItem(newTag: Tag) {
  set(editMode, true);
  set(tag, newTag);
}

function showDeleteConfirmation(selectedTag: Tag) {
  show(
    {
      title: t('tag_manager.confirmation.title'),
      message: t('tag_manager.confirmation.message', {
        tagToDelete: selectedTag.name,
      }),
    },
    () => deleteTag(selectedTag.name),
  );
}

function handleCreateTagClick() {
  set(editMode, false);
  set(tag, defaultTag());
}
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
          <RuiIcon name="add-line" />
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
        prepend-icon="search-line"
        :label="t('common.actions.search')"
        hide-details
      />
      <RuiDataTable
        dense
        :rows="tags"
        row-attr="name"
        :cols="headers"
        :search="search"
        outlined
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
    />
  </TablePageLayout>
</template>
