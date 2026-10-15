<script setup lang="ts">
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import TagIcon from '@/modules/tags/TagIcon.vue';

const { tags = [], small = false, wrapperClass = '', clickable = false } = defineProps<{
  tags?: string[];
  small?: boolean;
  wrapperClass?: string;
  /** Each tag becomes a button that emits `select`, e.g. to filter a table by it. */
  clickable?: boolean;
}>();

const emit = defineEmits<{
  select: [tag: string];
}>();

const { t } = useI18n({ useScope: 'global' });
const { allTags } = storeToRefs(useSessionMetadataStore());

function select(tag: string): void {
  if (clickable)
    emit('select', tag);
}
</script>

<template>
  <div
    v-if="tags && tags.length > 0"
    class="mt-2 flex flex-wrap items-center gap-1"
    :class="wrapperClass"
  >
    <TagIcon
      v-for="tag in tags"
      :key="tag"
      :small="small"
      :tag="allTags[tag]"
      v-bind="clickable ? { clickable: true, title: t('tag_display.filter_by', { tag }) } : {}"
      @click="select(tag)"
    />
  </div>
</template>
