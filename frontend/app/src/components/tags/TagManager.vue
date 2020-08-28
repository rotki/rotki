<template>
  <v-card light class="tag-manager">
    <v-card-title>
      Tag Manager
      <v-spacer v-if="dialog" />
      <v-btn v-if="dialog" class="tag-manager__close" icon text @click="close">
        <v-icon>mdi-close</v-icon>
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
      />

      <v-divider />

      <v-row no-gutters justify="space-between" align="end">
        <v-col cols="8">
          <h3>My Tags</h3>
        </v-col>
        <v-col cols="4">
          <v-text-field
            v-model="search"
            append-icon="mdi-magnify"
            label="Search"
            single-line
            hide-details
          />
        </v-col>
      </v-row>
      <v-data-table
        :items="tags"
        item-key="name"
        :headers="headers"
        :search="search"
        :footer-props="footerProps"
      >
        <template #item.name="{ item }">
          <tag-icon :tag="item" />
        </template>
        <template #item.action="{ item }">
          <v-icon small class="mr-2" @click="editItem(item)">
            mdi-pencil
          </v-icon>
          <v-icon small class="mr-2" @click="deleteItem(item)">
            mdi-delete
          </v-icon>
        </template>
      </v-data-table>
      <confirm-dialog
        title="Confirm tag deletion"
        :message="`Are you sure you want to delete ${tagToDelete}? This will also remove all mappings of this tag.`"
        :display="!!tagToDelete"
        @confirm="confirmDelete"
        @cancel="tagToDelete = ''"
      />
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import TagCreator from '@/components/tags/TagCreator.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { defaultTag } from '@/components/tags/types';
import { footerProps } from '@/config/datatable.common';
import { Tag } from '@/typing/types';

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

  footerProps = footerProps;

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

<style scoped lang="scss">
@import '@/scss/scroll';

::v-deep {
  .v-dialog {
    &__content {
      .v-dialog {
        &--active {
          @extend .themed-scrollbar;
        }
      }
    }
  }
}

.tag-manager {
  overflow: auto;
  height: 100%;
}
</style>
