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
          <v-row no-gutters>
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
      width: '80'
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
