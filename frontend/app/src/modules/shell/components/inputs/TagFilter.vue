<script setup lang="ts">
import type { Tag } from '@/modules/tags/tags';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import TagIcon from '@/modules/tags/TagIcon.vue';

const model = defineModel<string[]>({ required: true });

const { disabled = false, hideDetails = false } = defineProps<{
  disabled?: boolean;
  hideDetails?: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const { allTags } = storeToRefs(useSessionMetadataStore());

const availableTagsList = computed<Tag[]>(() => {
  const tags = get(allTags);
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
    :item-height="37"
    clearable
    dense
    :hide-details="hideDetails"
  >
    <template #selection="{ item, chipAttrs }">
      <TagIcon
        :tag="item"
        small
        class="!leading-4"
        closeable
        clickable
        v-bind="chipAttrs"
      />
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
