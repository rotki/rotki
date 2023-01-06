<script setup lang="ts">
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const enableAliasNames = ref<boolean>(true);
const { enableAliasNames: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(enableAliasNames, get(enabled));
});

const { tc } = useI18n();
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="enableAliasNames"
    frontend-setting
    :error-message="tc('frontend_settings.validation.enable_alias_names.error')"
  >
    <v-switch
      v-model="enableAliasNames"
      class="general-settings__fields__enable_alias_names mb-4 mt-2"
      :label="tc('frontend_settings.label.enable_alias_names')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>
