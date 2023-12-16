<script setup lang="ts">
import { type Tag, defaultTag } from '@/types/tags';
import type { DataTableColumn } from '@rotki/ui-library';

withDefaults(
  defineProps<{
    dialog?: boolean;
  }>(),
  {
    dialog: false,
  },
);

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const store = useTagStore();
const { addTag, editTag, deleteTag } = store;
const { tags } = storeToRefs(store);

const tag = ref<Tag>(defaultTag());
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
    cellClass: 'w-full !text-sm !text-rui-text-secondary',
  },
  {
    label: t('common.actions_text'),
    key: 'action',
    sortable: false,
  },
]);

const close = () => emit('close');

async function save({ tag: newTag, close: closeModal }: { tag: Tag; close?: boolean }) {
  const status = await (get(editMode) ? editTag(newTag) : addTag(newTag));

  if (status.success) {
    set(tag, defaultTag());
    set(editMode, false);
    closeModal && close();
  }
}

function cancel() {
  set(tag, defaultTag());
  set(editMode, false);
}

function editItem(newTag: Tag) {
  set(editMode, false);
  set(tag, newTag);
  nextTick(() => {
    set(editMode, true);
  });
}

const { show } = useConfirmStore();

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
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="p-4 text-rui-text">
        <div class="flex items-center gap-4">
          <div class="text-h6">
            {{ t('tag_manager.title') }}
          </div>
          <template v-if="dialog">
            <div class="grow" />
            <RuiButton
              data-cy="tag-manager__close"
              icon
              size="sm"
              variant="text"
              @click="close()"
            >
              <RuiIcon name="close-line" />
            </RuiButton>
          </template>
        </div>
        <div class="text-caption">
          {{ t('tag_manager.subtitle') }}
        </div>
      </div>
    </template>

    <TagCreator
      :tag="tag"
      :edit-mode="editMode"
      @update:tag="tag = $event"
      @cancel="cancel()"
      @save="save($event)"
    />

    <RuiDivider class="my-6" />

    <div class="flex flex-col gap-4">
      <div class="text-h6">
        {{ t('tag_manager.my_tags') }}
      </div>
      <div class="flex flex-row-reverse">
        <RuiTextField
          v-model="search"
          variant="outlined"
          color="primary"
          dense
          class="w-[22rem]"
          prepend-icon="search-line"
          :label="t('common.actions.search')"
          hide-details
        />
      </div>
      <RuiDataTable
        dense
        :rows="tags"
        row-attr="name"
        :cols="headers"
        :search="search"
        outlined
      >
        <template #item.name="{ row }">
          <TagIcon
            :tag="row"
            small
          />
        </template>
        <template #item.action="{ row }">
          <RowActions
            v-if="!row.readOnly"
            @edit-click="editItem(row)"
            @delete-click="showDeleteConfirmation(row)"
          />
        </template>
      </RuiDataTable>
    </div>
  </RuiCard>
</template>
