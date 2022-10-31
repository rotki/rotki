<template>
  <v-autocomplete
    :value="value"
    :disabled="disabled"
    :items="availableTagsList"
    class="tag-filter"
    small-chips
    :label="t('tag_filter.label')"
    prepend-inner-icon="mdi-magnify"
    item-text="name"
    :menu-props="{ closeOnContentClick: true }"
    outlined
    dense
    item-value="name"
    multiple
    clearable
    :hide-details="hideDetails"
    @input="input"
    @click:clear="input([])"
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
  </v-autocomplete>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import TagIcon from '@/components/tags/TagIcon.vue';
import { useTagStore } from '@/store/session/tags';
import { Tag } from '@/types/user';

const props = defineProps({
  value: { required: true, type: Array as PropType<string[]> },
  disabled: { required: false, default: false, type: Boolean },
  hideDetails: { required: false, default: false, type: Boolean }
});

const emit = defineEmits(['input']);
const { value } = toRefs(props);

const { t } = useI18n();

const { availableTags } = storeToRefs(useTagStore());

const availableTagsList = computed<Tag[]>(() => {
  const tags = get(availableTags);
  return Object.values(tags);
});

const input = (tags: string[]) => {
  emit('input', tags);
};

const remove = (tag: string) => {
  const tags = get(value);
  const index = tags.indexOf(tag);
  input([...tags.slice(0, index), ...tags.slice(index + 1)]);
};
</script>

<style scoped lang="scss">
.tag-filter {
  &__clear {
    margin-top: -4px;
  }

  :deep() {
    .v-select {
      &__slot {
        min-height: 40px;
      }
    }
  }
}
</style>
