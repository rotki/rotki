<script setup lang="ts">
import { RuiButton, RuiIcon } from '@rotki/ui-library';
import { useI18n } from 'vue-i18n';
import CalendarSettingsMenu from '@/modules/calendar/CalendarSettingsMenu.vue';

const emit = defineEmits<{
  add: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButton
    color="primary"
    data-testid="calendar-add-event"
    @click="emit('add')"
  >
    <template #prepend>
      <RuiIcon name="lu-plus" />
    </template>
    {{ t('calendar.add_event') }}
  </RuiButton>
  <CalendarSettingsMenu />
</template>
