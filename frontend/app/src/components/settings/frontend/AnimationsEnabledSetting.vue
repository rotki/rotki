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
import { set } from '@vueuse/core';
import { getSessionState } from '@/composables/session';

const animationsEnabled = ref<boolean>(true);

onMounted(() => {
  const state = getSessionState();
  set(animationsEnabled, state.animationsEnabled);
});
</script>
