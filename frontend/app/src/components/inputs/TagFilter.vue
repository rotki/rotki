<script setup lang="ts">
import { type Tag } from '@/types/tags';

const props = withDefaults(
  defineProps<{
    value: string[];
    disabled?: boolean;
    hideDetails?: boolean;
  }>(),
  {
    disabled: false,
    hideDetails: false
  }
);

const emit = defineEmits<{ (e: 'input', tags: string[]): void }>();
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

<template>
  <VAutocomplete
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
    @input="input($event)"
    @click:clear="input([])"
  >
    <template #selection="{ item, select }">
      <RuiChip
        label
        size="sm"
        class="font-medium m-0.5"
        :bg-color="`#${item.backgroundColor}`"
        :text-color="`#${item.foregroundColor}`"
        closeable
        @click:close="remove(item.name)"
        @click="select($event)"
      >
        {{ item.name }}
      </RuiChip>
    </template>
    <template #item="{ item }">
      <TagIcon :tag="item" small />
      <span class="tag-input__tag__description ml-4">
        {{ item.description }}
      </span>
    </template>
  </VAutocomplete>
</template>

<style scoped lang="scss">
.tag-filter {
  &__clear {
    margin-top: -4px;
  }

  /* stylelint-disable selector-class-pattern,selector-nested-pattern */

  :deep(.v-select__slot) {
    min-height: 40px;
  }

  /* stylelint-enable selector-class-pattern,selector-nested-pattern */
}
</style>
