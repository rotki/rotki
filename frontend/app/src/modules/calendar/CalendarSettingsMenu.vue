<script setup lang="ts">
import GoogleCalendarIntegration from '@/modules/calendar/GoogleCalendarIntegration.vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });

const showMenu = ref<boolean>(false);
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    :class-names="{ menu: 'w-full max-w-96' }"
    :options="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :options="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            class="text-rui-text-secondary!"
            :aria-label="t('calendar.dialog.settings.tooltip')"
            v-bind="attrs"
          >
            <RuiIcon name="lu-sliders-horizontal" />
          </RuiButton>
        </template>
        <span>{{ t('calendar.dialog.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <div class="flex flex-col">
      <div class="flex flex-col px-4 pt-3">
        <div class="mb-2 text-sm font-semibold text-rui-text">
          {{ t('calendar.dialog.settings.title') }}
        </div>
        <SettingSwitch
          setting="autoCreateCalendarReminders"
          size="sm"
          :label="t('calendar.dialog.settings.auto_create_reminders')"
        />
        <SettingSwitch
          setting="autoDeleteCalendarEntries"
          size="sm"
          :label="t('calendar.dialog.settings.auto_delete')"
        />
      </div>
      <GoogleCalendarIntegration />
    </div>
  </RuiMenu>
</template>
