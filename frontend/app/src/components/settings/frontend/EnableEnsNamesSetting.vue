<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const enableAliasNames = ref<boolean>(true);
const { enableAliasNames: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(enableAliasNames, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="enableAliasNames"
    frontend-setting
    :error-message="t('frontend_settings.alias_names.validation.error')"
  >
    <RuiSwitch
      v-model="enableAliasNames"
      class="mt-4"
      :label="t('frontend_settings.alias_names.label')"
      :messages="success"
      :error-messages="error"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
