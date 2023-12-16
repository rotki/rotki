<script setup lang="ts">
import type { Tag } from '@/types/tags';

const props = withDefaults(
  defineProps<{
    modelValue: string[];
    disabled?: boolean;
    hideDetails?: boolean;
  }>(),
  {
    disabled: false,
    hideDetails: false,
  },
);

const emit = defineEmits<{ (e: 'update:model-value', tags: string[]): void }>();

const model = useSimpleVModel(props, emit);

const { t } = useI18n();

const { availableTags } = storeToRefs(useTagStore());

const availableTagsList = computed<Tag[]>(() => {
  const tags = get(availableTags);
  return Object.values(tags);
});

function remove(tag: string) {
  const tags = get(model);
  const index = tags.indexOf(tag);
  set(model, [...tags.slice(0, index), ...tags.slice(index + 1)]);
}
</script>

<template>
  <VAutocomplete
    v-model="model"
    :disabled="disabled"
    :items="availableTagsList"
    class="tag-filter"
    small-chips
    :label="t('tag_filter.label')"
    prepend-inner-icon="mdi-magnify"
    item-title="name"
    :menu-props="{ closeOnContentClick: true }"
    variant="outlined"
    density="compact"
    item-value="name"
    multiple
    clearable
    :hide-details="hideDetails"
    @click:clear="model = []"
  >
    <template #selection="{ item }">
      <RuiChip
        tile
        size="sm"
        class="font-medium m-0.5"
        :bg-color="`#${item.raw.backgroundColor}`"
        :text-color="`#${item.raw.foregroundColor}`"
        closeable
        @click:close="remove(item.raw.name)"
        @click="model = [...model, item.raw.name]"
      >
        {{ item.raw.name }}
      </RuiChip>
    </template>
    <template #item="{ item }">
      <TagIcon
        :tag="item.raw"
        small
      />
      <span class="tag-input__tag__description ml-4">
        {{ item.raw.description }}
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
