<template>
  <div>
    <v-autocomplete
      :value="value"
      :disabled="disabled"
      :items="tags"
      class="tag-input"
      small-chips
      label="Tags"
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
        <template v-if="typeof item !== 'object'">
          <v-list-item-content v-text="item"></v-list-item-content>
        </template>
        <template v-else>
          <div>
            <tag-icon :tag="item"></tag-icon>
            <span class="tag-input__tag__description">
              {{ item.description }}
            </span>
          </div>
        </template>
      </template>
      <template #append-outer>
        <v-btn
          class="tag-input__manage-tags"
          icon
          text
          color="primary"
          :disabled="disabled"
          @click="manageTags = true"
        >
          <v-icon>fa-edit</v-icon>
        </v-btn>
      </template>
    </v-autocomplete>
    <v-dialog :value="!!manageTags" max-width="800" @input="manageTags = false">
      <tag-manager
        v-if="!!manageTags"
        dialog
        @close="manageTags = false"
      ></tag-manager>
    </v-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import TagIcon from '@/components/tags/TagIcon.vue';
import TagManager from '@/components/tags/TagManager.vue';
import { Tag } from '@/typing/types';

const { mapGetters } = createNamespacedHelpers('session');

@Component({
  components: { TagIcon, TagManager },
  computed: {
    ...mapGetters(['tags'])
  }
})
export default class TagInput extends Vue {
  @Prop({ required: true })
  value!: string[];
  @Prop({ required: false, default: false, type: Boolean })
  disabled!: boolean;
  tags!: Tag[];
  manageTags: boolean = false;

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
.tag-input {
  &__tag {
    &__description {
      padding-left: 18px;
    }
  }
}
</style>
