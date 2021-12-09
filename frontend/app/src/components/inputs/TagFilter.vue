<template>
  <v-autocomplete
    :value="value"
    :disabled="disabled"
    :items="availableTagsArray"
    class="tag-filter"
    small-chips
    :label="$t('tag_filter.label')"
    prepend-inner-icon="mdi-magnify"
    item-text="name"
    :menu-props="{ closeOnContentClick: true }"
    outlined
    dense
    item-value="name"
    multiple
    @input="input"
  >
    <template #selection="{ item, selected, select }">
      <v-chip
        label
        small
        class="font-weight-medium"
        :input-value="selected"
        :color="`#${item.backgroundColor}`"
        :text-color="`#${item.foregroundColor}`"
        close
        @click:close="remove(item.name)"
        @click="select"
      >
        {{ item.name }}
      </v-chip>
    </template>
    <template #item="{ item }">
      <tag-icon :tag="item" />
      <span class="tag-input__tag__description ml-4">
        {{ item.description }}
      </span>
    </template>
    <template #append-outer>
      <v-btn icon text class="tag-filter__clear" @click="input([])">
        <v-icon>mdi-close</v-icon>
      </v-btn>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import TagIcon from '@/components/tags/TagIcon.vue';
import { Tag } from '@/types/user';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: {
    TagIcon
  },
  computed: {
    ...mapGetters(['availableTagsArray'])
  }
})
export default class TagFilter extends Vue {
  @Prop({ required: true })
  value!: string[];
  @Prop({ required: false, default: false, type: Boolean })
  disabled!: boolean;
  availableTagsArray!: Tag[];

  filter(tag: Tag, queryText: string): boolean {
    const { name, description } = tag;
    const query = queryText.toLocaleLowerCase();
    return (
      name.toLocaleLowerCase().indexOf(query) > -1 ||
      description.toLocaleLowerCase().indexOf(query) > -1
    );
  }

  remove(tag: string) {
    const tags = this.value;
    const index = tags.indexOf(tag);
    this.input([...tags.slice(0, index), ...tags.slice(index + 1)]);
  }

  @Emit()
  input(_value: string[]) {}
}
</script>

<style scoped lang="scss">
.tag-filter {
  &__clear {
    margin-top: -4px;
  }

  ::v-deep {
    .v-select {
      &__slot {
        min-height: 40px;
      }
    }
  }
}
</style>
