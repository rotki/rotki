<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const value = ref<boolean>(false);
const { autoDetectTokens } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(value, get(autoDetectTokens));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    setting="autoDetectTokens"
    :error-message="t('general_settings.auto_detect_tokens.validation.error')"
  >
    <template #title>
      {{ t('general_settings.auto_detect_tokens.title') }}
    </template>
    <template
      #default="{ error, success, updateImmediate }"
    >
      <RuiSwitch
        v-model="value"
        color="primary"
        :label="t('general_settings.auto_detect_tokens.label')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </template>
  </SettingsOption>
</template>
