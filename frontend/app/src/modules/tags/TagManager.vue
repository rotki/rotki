<script setup lang="ts">
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import RowActions from '@/modules/shell/components/RowActions.vue';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import TagFormDialog from '@/modules/tags/TagFormDialog.vue';
import TagIcon from '@/modules/tags/TagIcon.vue';
import { defaultTag, isReservedTag, type Tag } from '@/modules/tags/tags';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

const { t } = useI18n({ useScope: 'global' });

const tag = ref<Tag | undefined>(undefined);
const editMode = ref<boolean>(false);
const search = ref<string>('');
const originalName = ref<string>('');

const route = useRoute();
const router = useRouter();

const { tags } = storeToRefs(useSessionMetadataStore());
const { deleteTag } = useTagOperations();
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
            v-if="!isReservedTag(row.name)"
            @edit-click="editItem(row)"
            @delete-click="showDeleteConfirmation(row)"
          />
          <span
            v-else
            class="text-rui-text-secondary"
          >
            -
          </span>
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
