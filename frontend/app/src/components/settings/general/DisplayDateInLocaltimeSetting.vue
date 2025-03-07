<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const displayDateInLocaltime = ref<boolean>(true);
const { displayDateInLocaltime: enabled } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(displayDateInLocaltime, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="displayDateInLocaltime"
    :error-message="t('general_settings.display_date_in_localtime.validation.error')"
  >
    <RuiSwitch
      v-model="displayDateInLocaltime"
      color="primary"
      :label="t('general_settings.display_date_in_localtime.label')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
