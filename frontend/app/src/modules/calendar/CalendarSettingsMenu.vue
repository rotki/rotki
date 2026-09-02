<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import GoogleCalendarIntegration from '@/modules/calendar/GoogleCalendarIntegration.vue';
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import CardTitle from '@/modules/shell/components/CardTitle.vue';

const { t } = useI18n({ useScope: 'global' });

const showMenu = ref(false);
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    :class-names="{ menu: 'w-full max-w-96 !bg-transparent' }"
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
            color="primary"
            size="lg"
            v-bind="attrs"
          >
            <RuiIcon name="lu-settings" />
          </RuiButton>
        </template>
        <span>{{ t('calendar.dialog.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <div class="p-4">
      <CardTitle class="pb-6">
        {{ t('calendar.dialog.settings.title') }}
      </CardTitle>
      <div class="flex flex-col gap-1">
        <SettingSwitch
          setting="autoCreateCalendarReminders"
          :label="t('calendar.dialog.settings.auto_create_reminders')"
        />
        <SettingSwitch
          setting="autoDeleteCalendarEntries"
          :label="t('calendar.dialog.settings.auto_delete')"
        />

        <!-- Google Calendar Integration -->
        <GoogleCalendarIntegration />
      </div>
      <div class="flex justify-end">
        <RuiButton
          class="ml-auto"
          variant="text"
          color="primary"
          @click="showMenu = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </div>
  </RuiMenu>
</template>
