<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';

const displayDateInLocaltime = ref<boolean>(true);
const enabled = useSetting('displayDateInLocaltime');

onMounted(() => {
  set(displayDateInLocaltime, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });
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
