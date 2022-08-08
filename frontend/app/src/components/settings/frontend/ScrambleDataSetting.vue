<template>
  <settings-option
    #default="{ error, success, update }"
    setting="scrambleData"
    session-setting
    :error-message="$tc('frontend_settings.validation.scramble.error')"
  >
    <v-switch
      v-model="scrambleData"
      class="general-settings__fields__scramble-data"
      :label="$t('frontend_settings.label.scramble')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSessionSettingsStore } from '@/store/settings/session';

const { scrambleData: enabled } = useSessionSettingsStore();

const scrambleData = ref<boolean>(false);
onMounted(() => {
  set(scrambleData, get(enabled));
});
</script>
