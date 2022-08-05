<template>
  <settings-option
    #default="{ error, success, update }"
    setting="animationsEnabled"
    session-setting
    :transform="value => !value"
    :error-message="$tc('frontend_settings.validation.animations.error')"
  >
    <v-switch
      :value="!animationsEnabled"
      class="general-settings__fields__animation-enabled mt-0"
      :label="$t('frontend_settings.label.animations')"
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
import { useSessionSettingsStore } from '@/store/settings/session';

const animationsEnabled = ref<boolean>(true);

const { animationsEnabled: enabled } = storeToRefs(useSessionSettingsStore());

onMounted(() => {
  set(animationsEnabled, get(enabled));
});
</script>
