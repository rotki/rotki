<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { type Tag, defaultTag } from '@/types/tags';

defineProps({
  dialog: { required: false, type: Boolean, default: false }
});

const emit = defineEmits(['close']);

const store = useTagStore();
const { addTag, editTag, deleteTag } = store;
const { tags } = storeToRefs(store);

const tag = ref<Tag>(defaultTag());
const editMode = ref<boolean>(false);
const search = ref<string>('');

const { tc } = useI18n();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: tc('common.name'),
    value: 'name',
    width: '200'
  },
  {
    text: tc('common.description'),
    value: 'description'
  },
  {
    text: tc('tag_manager.headers.actions'),
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
      title: tc('tag_manager.confirmation.title'),
      message: tc('tag_manager.confirmation.message', 0, {
        tagToDelete: selectedTag.name
      })
    },
    () => deleteTag(selectedTag.name)
  );
};
</script>

<template>
  <card class="tag-manager">
    <template #title>
      {{ tc('tag_manager.title') }}
    </template>
    <template v-if="dialog" #details>
      <v-btn class="tag-manager__close" icon text @click="close()">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </template>
    <template #subtitle>
      {{ tc('tag_manager.subtitle') }}
    </template>
    <tag-creator
      :tag="tag"
      :edit-mode="editMode"
      @changed="onChange($event)"
      @cancel="cancel()"
      @save="save($event)"
    />

    <v-divider />

    <div class="mx-n4">
      <card outlined-body flat>
        <template #title>
          {{ tc('tag_manager.my_tags') }}
        </template>
        <template #search>
          <v-row justify="end">
            <v-col cols="12" sm="5">
              <v-text-field
                v-model="search"
                outlined
                dense
                class="mb-4"
                prepend-inner-icon="mdi-magnify"
                :label="tc('common.actions.search')"
                single-line
                hide-details
                clearable
              />
            </v-col>
          </v-row>
        </template>
        <data-table
          :items="tags"
          item-key="name"
          :headers="headers"
          :search="search"
        >
          <template #item.name="{ item }">
            <tag-icon :tag="item" />
          </template>
          <template #item.action="{ item }">
            <v-row v-if="!item.readOnly" no-gutters>
              <v-col>
                <v-icon small class="mr-2" @click="editItem(item)">
                  mdi-pencil
                </v-icon>
              </v-col>
              <v-col>
                <v-icon
                  small
                  class="mr-2"
                  @click="showDeleteConfirmation(item)"
                >
                  mdi-delete
                </v-icon>
              </v-col>
            </v-row>
          </template>
        </data-table>
      </card>
    </div>
  </card>
</template>

<style scoped lang="scss">
.tag-manager {
  overflow: auto;
  height: 100%;
}
</style>
