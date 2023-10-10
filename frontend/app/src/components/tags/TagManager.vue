<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
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

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('common.name'),
    value: 'name',
    width: '200'
  },
  {
    text: t('common.description'),
    value: 'description'
  },
  {
    text: t('common.actions_text'),
    value: 'action',
    sortable: false,
    width: '80'
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
  <Card class="tag-manager">
    <template #title>
      {{ t('tag_manager.title') }}
    </template>
    <template v-if="dialog" #details>
      <VBtn class="tag-manager__close" icon text @click="close()">
        <VIcon>mdi-close</VIcon>
      </VBtn>
    </template>
    <template #subtitle>
      {{ t('tag_manager.subtitle') }}
    </template>
    <TagCreator
      :tag="tag"
      :edit-mode="editMode"
      @changed="onChange($event)"
      @cancel="cancel()"
      @save="save($event)"
    />

    <div>
      <Card flat>
        <template #title>
          {{ t('tag_manager.my_tags') }}
        </template>
        <template #search>
          <VRow justify="end">
            <VCol cols="12" sm="5">
              <VTextField
                v-model="search"
                outlined
                dense
                class="mb-4"
                prepend-inner-icon="mdi-magnify"
                :label="t('common.actions.search')"
                single-line
                hide-details
                clearable
              />
            </VCol>
          </VRow>
        </template>
        <DataTable
          :items="tags"
          item-key="name"
          :headers="headers"
          :search="search"
        >
          <template #item.name="{ item }">
            <TagIcon :tag="item" />
          </template>
          <template #item.action="{ item }">
            <VRow v-if="!item.readOnly" no-gutters>
              <VCol>
                <VIcon small class="mr-2" @click="editItem(item)">
                  mdi-pencil
                </VIcon>
              </VCol>
              <VCol>
                <VIcon small class="mr-2" @click="showDeleteConfirmation(item)">
                  mdi-delete
                </VIcon>
              </VCol>
            </VRow>
          </template>
        </DataTable>
      </Card>
    </div>
  </Card>
</template>

<style scoped lang="scss">
.tag-manager {
  overflow: auto;
  height: 100%;
}
</style>
