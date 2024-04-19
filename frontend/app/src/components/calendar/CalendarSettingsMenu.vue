<script setup lang="ts">
const { t } = useI18n();

const showMenu = ref(false);
const autoDelete = ref(true);
const autoCreateReminders = ref(true);

const { autoDeleteCalendarEntries, autoCreateCalendarReminders } = storeToRefs(
  useGeneralSettingsStore(),
);

function setAutoDelete() {
  set(autoDelete, get(autoDeleteCalendarEntries));
}

function setAutoCreate() {
  set(autoCreateReminders, get(autoCreateCalendarReminders) ?? true); // todo: remove `?? true` when backend is merged
}

onMounted(() => {
  setAutoDelete();
  setAutoCreate();
});
</script>

<template>
  <RuiMenu
    v-model="showMenu"
    menu-class="w-full max-w-96"
    :popper="{ placement: 'bottom-end' }"
  >
    <template #activator="{ on }">
      <RuiTooltip
        :popper="{ placement: 'top' }"
        :open-delay="400"
      >
        <template #activator>
          <RuiButton
            variant="text"
            size="sm"
            icon
            v-on="on"
          >
            <RuiIcon name="settings-4-line" />
          </RuiButton>
        </template>
        <span>{{ t('calendar.dialog.settings.tooltip') }}</span>
      </RuiTooltip>
    </template>
    <RuiCard variant="flat">
      <template #header>
        {{ t('calendar.dialog.settings.title') }}
      </template>
      <div class="flex flex-col gap-4">
        <SettingsOption
          #default="{ updateImmediate, loading }"
          setting="autoDeleteCalendarEntries"
          @finished="setAutoDelete()"
        >
          <RuiSwitch
            v-model="autoDelete"
            :disabled="loading"
            :label="t('calendar.dialog.settings.auto_delete')"
            color="primary"
            hide-details
            @input="updateImmediate($event)"
          />
        </SettingsOption>
        <SettingsOption
          #default="{ updateImmediate, loading }"
          setting="autoCreateCalendarReminders"
          @finished="setAutoCreate()"
        >
          <RuiSwitch
            v-model="autoCreateReminders"
            :disabled="loading"
            :label="t('calendar.dialog.settings.auto_create_reminders')"
            color="primary"
            hide-details
            @input="updateImmediate($event)"
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
