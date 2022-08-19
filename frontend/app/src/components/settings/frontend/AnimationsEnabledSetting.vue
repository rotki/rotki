<template>
  <settings-option
    #default="{ error, success, update }"
    setting="animationsEnabled"
    session-setting
    :transform="transform"
    :error-message="tc('frontend_settings.validation.animations.error')"
  >
    <v-switch
      :value="!animationsEnabled"
      class="general-settings__fields__animation-enabled mt-0"
      :label="tc('frontend_settings.label.animations')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useI18n } from 'vue-i18n-composable';
import { useSessionSettingsStore } from '@/store/settings/session';

const animationsEnabled = ref<boolean>(true);
const { tc } = useI18n();

const { animationsEnabled: enabled } = storeToRefs(useSessionSettingsStore());
const transform = (value: boolean) => !value;

onMounted(() => {
  set(animationsEnabled, get(enabled));
});
</script>
