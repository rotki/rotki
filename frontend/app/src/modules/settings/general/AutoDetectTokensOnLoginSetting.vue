<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const value = ref<boolean>(false);
const { autoDetectTokensOnLogin } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(value, get(autoDetectTokensOnLogin));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    frontend-setting
    setting="autoDetectTokensOnLogin"
    :error-message="t('general_settings.auto_detect_tokens_on_login.validation.error')"
  >
    <template #title>
      {{ t('general_settings.auto_detect_tokens_on_login.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.auto_detect_tokens_on_login.subtitle') }}
    </template>
    <template #default="{ error, success, updateImmediate }">
      <RuiSwitch
        v-model="value"
        color="primary"
        data-cy="auto-detect-tokens-on-login-toggle"
        :label="t('general_settings.auto_detect_tokens_on_login.label')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
