<template>
  <v-autocomplete
    :value="value"
    :disabled="disabled"
    :items="tags"
    class="tag-filter"
    small-chips
    label="Filter"
    prepend-inner-icon="fa-search"
    item-text="name"
    :menu-props="{ closeOnClick: true, closeOnContentClick: true }"
    item-value="name"
    multiple
    @input="input"
  >
    <template #selection="{ item, selected, select }">
      <v-chip
        label
        class="font-weight-medium"
        :input-value="selected"
        :color="`#${item.background_color}`"
        :text-color="`#${item.foreground_color}`"
        close
        @click:close="remove(item.name)"
        @click="select"
      >
        {{ item.name }}
      </v-chip>
    </template>
    <template #item="{ item }">
      <template>
        <div>
          <tag-icon :tag="item"></tag-icon>
          <span class="tag-input__tag__description">
            {{ item.description }}
          </span>
        </div>
      </template>
    </template>
    <template #append-outer>
      <v-btn icon text class="tag-filter__clear" @click="input([])">
        <v-icon>fa-times</v-icon>
      </v-btn>
    </template>
  </v-autocomplete>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import TagIcon from '@/components/tags/TagIcon.vue';
import { Tag } from '@/typing/types';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: {
    TagIcon
  },
  computed: {
    ...mapGetters(['tags'])
  }
})
export default class TagFilter extends Vue {
  @Prop({ required: true })
  value!: string[];
  @Prop({ required: false, default: false, type: Boolean })
  disabled!: boolean;
  tags!: Tag[];

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
}
</style>
