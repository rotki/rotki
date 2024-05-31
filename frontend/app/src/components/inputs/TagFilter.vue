<script setup lang="ts">
import type { Tag } from '@/types/tags';

const props = withDefaults(
  defineProps<{
    value: string[];
    disabled?: boolean;
    hideDetails?: boolean;
  }>(),
  {
    disabled: false,
    hideDetails: false,
  },
);

const emit = defineEmits<{ (e: 'input', tags: string[]): void }>();
const { value } = toRefs(props);

const { t } = useI18n();

const { availableTags } = storeToRefs(useTagStore());

const availableTagsList = computed<Tag[]>(() => {
  const tags = get(availableTags);
  return Object.values(tags);
});

function input(tags: string[]) {
  emit('input', tags);
}
</script>

<template>
  <RuiAutoComplete
    :value="value"
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
    @input="input($event)"
  >
    <template #selection="{ item, chipOn, chipAttrs }">
      <RuiChip
        tile
        size="sm"
        class="font-medium !leading-3"
        :bg-color="`#${item.backgroundColor}`"
        :text-color="`#${item.foregroundColor}`"
        closeable
        clickable
        v-bind="chipAttrs"
        v-on="chipOn"
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
