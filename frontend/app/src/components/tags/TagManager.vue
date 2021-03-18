<template>
  <v-card light class="tag-manager">
    <v-card-title>
      {{ $t('tag_manager.title') }}
      <v-spacer v-if="dialog" />
      <v-btn v-if="dialog" class="tag-manager__close" icon text @click="close">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </v-card-title>
    <v-card-subtitle v-text="$t('tag_manager.subtitle')" />
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
          <div class="text-h5" v-text="$t('tag_manager.my_tags')" />
        </v-col>
        <v-col cols="4">
          <v-text-field
            v-model="search"
            append-icon="mdi-magnify"
            :label="$t('tag_manager.search')"
            single-line
            hide-details
          />
        </v-col>
      </v-row>
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
          <v-icon small class="mr-2" @click="editItem(item)">
            mdi-pencil
          </v-icon>
          <v-icon small class="mr-2" @click="deleteItem(item)">
            mdi-delete
          </v-icon>
        </template>
      </data-table>
      <confirm-dialog
        :title="$t('tag_manager.confirmation.title')"
        :message="$t('tag_manager.confirmation.message', { tagToDelete })"
        :display="!!tagToDelete"
        @confirm="confirmDelete"
        @cancel="tagToDelete = ''"
      />
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapGetters } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import DataTable from '@/components/helper/DataTable.vue';
import TagCreator from '@/components/tags/TagCreator.vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { defaultTag } from '@/components/tags/types';
import { Tag } from '@/typing/types';

@Component({
  components: { DataTable, TagIcon, ConfirmDialog, TagCreator },
  computed: {
    ...mapGetters('session', ['tags'])
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

  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('tag_manager.headers.name').toString(),
      value: 'name',
      width: '200'
    },
    {
      text: this.$t('tag_manager.headers.description').toString(),
      value: 'description'
    },
    {
      text: this.$t('tag_manager.headers.actions').toString(),
      value: 'action',
      sortable: false,
      width: '50'
    }
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
@import '~@/scss/scroll';

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
