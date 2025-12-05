<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useNotesCount } from '@/composables/notes/use-notes-count';

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{ (e: 'update:visible', visible: boolean): void }>();

const { visible } = toRefs(props);
const { t } = useI18n({ useScope: 'global' });

function toggleVisibility(): void {
  emit('update:visible', !get(visible));
}

const { hasSpecialNotes, notesCount } = useNotesCount();
</script>

<template>
  <RuiBadge
    :model-value="hasSpecialNotes"
    color="primary"
    placement="top"
    size="sm"
    offset-y="14"
    offset-x="-12"
    :text="notesCount.toString()"
    class="flex items-center"
  >
    <MenuTooltipButton
      :tooltip="t('notes_menu.tooltip')"
      @click="toggleVisibility()"
    >
      <RuiIcon
        :class="visible ? 'help--visible' : null"
        name="lu-notebook"
      />
    </MenuTooltipButton>
  </RuiBadge>
</template>

<style scoped lang="scss">
.help {
  &--visible {
    transform: rotate(-25deg);
  }
}
</style>
