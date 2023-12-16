<script setup lang="ts">
import type { Tag } from '@/types/tags';

withDefaults(
  defineProps<{
    disabled?: boolean;
    hideDetails?: boolean;
  }>(),
  {
    disabled: false,
    hideDetails: false,
  },
);

const model = defineModel<string[]>({ required: true });

const { t } = useI18n();

const { availableTags } = storeToRefs(useTagStore());

const availableTagsList = computed<Tag[]>(() => {
  const tags = get(availableTags);
  return Object.values(tags);
});
</script>

<template>
  <RuiAutoComplete
    v-model="model"
    :disabled="disabled"
    :options="availableTagsList"
    class="tag-filter"
    :label="t('tag_filter.label')"
    key-attr="name"
    text-attr="name"
    variant="outlined"
    :item-height="40"
    clearable
    dense
    :hide-details="hideDetails"
  >
    <template #selection="{ item, chipAttrs }">
      <RuiChip
        tile
        size="sm"
        class="font-medium !leading-3"
        :bg-color="`#${item.backgroundColor}`"
        :text-color="`#${item.foregroundColor}`"
        closeable
        clickable
        v-bind="chipAttrs"
      >
        {{ item.name }}
      </RuiChip>
    </template>
    <template #item="{ item }">
      <TagIcon
        :tag="item"
        show-description
        small
      />
    </template>
  </RuiAutoComplete>
</template>
