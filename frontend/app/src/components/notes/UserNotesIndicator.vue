<script setup lang="ts">
import MenuTooltipButton from '@/components/helper/MenuTooltipButton.vue';
import { useNotesCount } from '@/composables/notes/use-notes-count';

const visible = defineModel<boolean>('visible', { required: true });

const { t } = useI18n({ useScope: 'global' });

function toggleVisibility(): void {
  set(visible, !get(visible));
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
        :class="{ '-rotate-[25deg]': visible }"
        name="lu-notebook"
      />
    </MenuTooltipButton>
  </RuiBadge>
</template>
