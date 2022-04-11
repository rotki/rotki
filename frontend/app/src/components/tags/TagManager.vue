<template>
  <card light class="tag-manager">
    <template #title>
      {{ $t('tag_manager.title') }}
    </template>
    <template v-if="dialog" #details>
      <v-btn class="tag-manager__close" icon text @click="close">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </template>
    <template #subtitle>
      {{ $t('tag_manager.subtitle') }}
    </template>
    <tag-creator
      :tag="tag"
      :edit-mode="editMode"
      @changed="onChange($event)"
      @cancel="cancel"
      @save="save"
    />

    <v-divider />

    <card outlined-body flat>
      <template #title>
        {{ $t('tag_manager.my_tags') }}
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
              :label="$t('tag_manager.search')"
              single-line
              hide-details
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
              <v-icon small class="mr-2" @click="deleteItem(item)">
                mdi-delete
              </v-icon>
            </v-col>
          </v-row>
        </template>
      </data-table>
    </card>

    <confirm-dialog
      :title="$t('tag_manager.confirmation.title')"
      :message="$t('tag_manager.confirmation.message', { tagToDelete })"
      :display="!!tagToDelete"
      @confirm="confirmDelete"
      @cancel="tagToDelete = ''"
    />
  </card>
</template>

<script lang="ts">
import { defineComponent, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { DataTableHeader } from 'vuetify';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TagCreator from '@/components/tags/TagCreator.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { defaultTag } from '@/components/tags/types';
import { setupTags } from '@/composables/session';
import i18n from '@/i18n';
import { Tag } from '@/types/user';

const headers: DataTableHeader[] = [
  {
    text: i18n.t('tag_manager.headers.name').toString(),
    value: 'name',
    width: '200'
  },
  {
    text: i18n.t('tag_manager.headers.description').toString(),
    value: 'description'
  },
  {
    text: i18n.t('tag_manager.headers.actions').toString(),
    value: 'action',
    sortable: false,
    width: '80'
  }
];

export default defineComponent({
  name: 'TagManager',
  components: { DataTable, TagIcon, ConfirmDialog, TagCreator },
  props: {
    dialog: { required: false, type: Boolean, default: false }
  },
  emits: ['close'],
  setup(_, { emit }) {
    const { tags, addTag, editTag, deleteTag } = setupTags();

    const tag = ref<Tag>(defaultTag());
    const editMode = ref<boolean>(false);
    const tagToDelete = ref<string>('');
    const search = ref<string>('');

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

    const deleteItem = (selectedTag: Tag) => {
      set(tagToDelete, selectedTag.name);
    };

    const confirmDelete = async () => {
      const tagName = get(tagToDelete);
      set(tagToDelete, '');
      await deleteTag(tagName);
    };

    return {
      headers,
      close,
      tags,
      tag,
      editMode,
      onChange,
      cancel,
      save,
      search,
      editItem,
      deleteItem,
      tagToDelete,
      confirmDelete
    };
  }
});
</script>

<style scoped lang="scss">
.tag-manager {
  overflow: auto;
  height: 100%;
}
</style>
