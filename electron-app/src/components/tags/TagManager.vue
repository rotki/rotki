<template>
  <v-card light>
    <v-card-title>
      Tag Manager
      <v-spacer v-if="dialog"></v-spacer>
      <v-btn v-if="dialog" icon text @click="close">
        <v-icon>fa-close</v-icon>
      </v-btn>
    </v-card-title>
    <v-card-subtitle>
      Create new tags or modify existing
    </v-card-subtitle>
    <v-card-text>
      <tag-creator
        :tag="tag"
        :edit-mode="editMode"
        @changed="onChange($event)"
        @cancel="cancel"
        @save="save"
      ></tag-creator>

      <v-divider></v-divider>

      <v-row no-gutters justify="space-between" align="end">
        <v-col cols="8">
          <h3>My Tags</h3>
        </v-col>
        <v-col cols="4">
          <v-text-field
            v-model="search"
            append-icon="fa-search"
            label="Search"
            single-line
            hide-details
          ></v-text-field>
        </v-col>
      </v-row>
      <v-data-table
        :items="tags"
        item-key="name"
        :headers="headers"
        :search="search"
      >
        <template #item.name="{ item }">
          <tag-icon :tag="item"></tag-icon>
        </template>
        <template #item.action="{ item }">
          <v-icon small class="mr-2" @click="editItem(item)">
            fa-edit
          </v-icon>
          <v-icon small class="mr-2" @click="deleteItem(item)">
            fa-trash
          </v-icon>
        </template>
      </v-data-table>
      <confirm-dialog
        title="Confirm tag deletion"
        :message="
          `Are you sure you want to delete ${tagToDelete}? This will also remove all mappings of this tag.`
        "
        :display="!!tagToDelete"
        @confirm="confirmDelete"
        @cancel="tagToDelete = ''"
      ></confirm-dialog>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import TagCreator from '@/components/tags/TagCreator.vue';
import { defaultTag } from '@/components/tags/types';
import { createNamespacedHelpers } from 'vuex';
import { Tag } from '@/typing/types';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import TagIcon from '@/components/tags/TagIcon.vue';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { TagIcon, ConfirmDialog, TagCreator },
  computed: {
    ...mapGetters(['tags'])
  }
})
export default class TagManager extends Vue {
  tags!: Tag[];
  tag: Tag = defaultTag();
  editMode: boolean = false;
  tagToDelete: string = '';

  search: string = '';

  @Prop({ required: false, default: false, type: Boolean })
  dialog!: boolean;

  @Emit()
  close() {}

  headers = [
    { text: 'Name', value: 'name', width: '200' },
    { text: 'Description', value: 'description' },
    { text: 'Actions', value: 'action', sortable: false, width: '50' }
  ];

  onChange(tag: Tag) {
    this.tag = tag;
  }

  async save(tag: Tag) {
    this.tag = defaultTag();
    if (this.editMode) {
      this.editMode = false;
      await this.$store.dispatch('session/editTag', tag);
    } else {
      await this.$store.dispatch('session/addTag', tag);
    }
  }

  cancel() {
    this.tag = defaultTag();
    this.editMode = false;
  }

  editItem(tag: Tag) {
    this.tag = tag;
    this.editMode = true;
  }

  deleteItem(tag: Tag) {
    this.tagToDelete = tag.name;
  }

  async confirmDelete() {
    const tagName = this.tagToDelete;
    this.tagToDelete = '';
    await this.$store.dispatch('session/deleteTag', tagName);
  }
}
</script>

<style scoped></style>
