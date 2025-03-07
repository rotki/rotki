<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const { t } = useI18n();

const showMenu = ref(false);
const autoDelete = ref(true);
const autoCreateReminders = ref(true);

const { autoCreateCalendarReminders, autoDeleteCalendarEntries } = storeToRefs(useGeneralSettingsStore());

function setAutoDelete() {
  set(autoDelete, get(autoDeleteCalendarEntries));
}

function setAutoCreate() {
  set(autoCreateReminders, get(autoCreateCalendarReminders));
}

onMounted(() => {
  setAutoDelete();
  setAutoCreate();
});
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    menu-class="w-full max-w-96 !bg-transparent"
    :popper="{ placement: 'bottom-end' }"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            v-bind="attrs"
          >
            <RuiIcon name="lu-settings" />
          </RuiButton>
        </template>
        <span>{{ t('calendar.dialog.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <RuiCard variant="flat">
      <template #header>
        {{ t('calendar.dialog.settings.title') }}
      </template>
      <div class="flex flex-col gap-1">
        <SettingsOption
          #default="{ updateImmediate, loading, error, success }"
          setting="autoCreateCalendarReminders"
          @finished="setAutoCreate()"
        >
          <RuiSwitch
            v-model="autoCreateReminders"
            :disabled="loading"
            :label="t('calendar.dialog.settings.auto_create_reminders')"
            color="primary"
            :error-messages="error"
            :success-messages="success"
            @update:model-value="updateImmediate($event)"
          />
        </SettingsOption>
        <SettingsOption
          #default="{ updateImmediate, loading, error, success }"
          setting="autoDeleteCalendarEntries"
          @finished="setAutoDelete()"
        >
          <RuiSwitch
            v-model="autoDelete"
            :disabled="loading"
            :label="t('calendar.dialog.settings.auto_delete')"
            color="primary"
            :error-messages="error"
            :success-messages="success"
            @update:model-value="updateImmediate($event)"
          />
        </SettingsOption>
      </div>
      <template #footer>
        <RuiButton
          class="ml-auto"
          variant="text"
          color="primary"
          @click="showMenu = false"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </template>
    </RuiCard>
  </RuiMenu>
</template>
