<script setup lang="ts">
import { type DataTableColumn } from '@rotki/ui-library-compat';
import { type Tag, defaultTag } from '@/types/tags';

withDefaults(
  defineProps<{
    dialog?: boolean;
  }>(),
  {
    dialog: false
  }
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

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('common.name'),
    key: 'name'
  },
  {
    label: t('common.description'),
    key: 'description',
    cellClass: 'w-full'
  },
  {
    label: t('common.actions_text'),
    key: 'action',
    sortable: false
  }
]);

const close = () => emit('close');

const onChange = (newTag: Tag) => {
  set(tag, newTag);
};

const save = async (newTag: Tag) => {
  set(tag, defaultTag());
  if (get(editMode)) {
    set(editMode, false);
    await editTag(newTag);
  } else {
    await addTag(newTag);
  }
};

const cancel = () => {
  set(tag, defaultTag());
  set(editMode, false);
};

const editItem = (newTag: Tag) => {
  set(tag, newTag);
  set(editMode, true);
};

const { show } = useConfirmStore();

const showDeleteConfirmation = (selectedTag: Tag) => {
  show(
    {
      title: t('tag_manager.confirmation.title'),
      message: t('tag_manager.confirmation.message', {
        tagToDelete: selectedTag.name
      })
    },
    () => deleteTag(selectedTag.name)
  );
};
</script>

<template>
  <RuiCard>
    <template #custom-header>
      <div class="p-4">
        <div class="flex items-center gap-4">
          <div class="text-h6">
            {{ t('tag_manager.title') }}
          </div>
          <template v-if="dialog">
            <div class="grow" />
            <RuiButton
              class="tag-manager__close"
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
      @changed="onChange($event)"
      @cancel="cancel()"
      @save="save($event)"
    />

    <RuiDivider class="p-4" />

    <div class="flex flex-col gap-4">
      <div class="text-h6">
        {{ t('tag_manager.my_tags') }}
      </div>
      <div class="flex flex-row-reverse">
        <RuiTextField
          v-model="search"
          variant="outlined"
          dense
          class="w-[22rem]"
          prepend-icon="search-line"
          :label="t('common.actions.search')"
          hide-details
        />
      </div>
      <RuiDataTable
        :rows="tags"
        row-attr="name"
        :cols="headers"
        :search="search"
        outlined
      >
        <template #item.name="{ row }">
          <TagIcon :tag="row" />
        </template>
        <template #item.action="{ row }">
          <div v-if="!row.readOnly" class="flex items-center gap-4">
            <RuiButton variant="text" icon size="sm" @click="editItem(row)">
              <RuiIcon name="pencil-line" />
            </RuiButton>
            <RuiButton
              variant="text"
              icon
              size="sm"
              @click="showDeleteConfirmation(row)"
            >
              <RuiIcon name="delete-bin-5-line" />
            </RuiButton>
          </div>
        </template>
      </RuiDataTable>
    </div>
  </RuiCard>
</template>
