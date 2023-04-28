<script setup lang="ts">
import { type Ref } from 'vue';

const abbreviate: Ref<boolean> = ref(false);
const { abbreviateNumber } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(abbreviate, get(abbreviateNumber));
});

const { tc } = useI18n();
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="abbreviateNumber"
    frontend-setting
  >
    <v-switch
      v-model="abbreviate"
      data-cy="frontend-settings__fields__abbreviate_number"
      :label="tc('frontend_settings.label.abbreviate_number')"
      :hint="tc('frontend_settings.subtitle.abbreviate_number')"
      color="primary"
      persistent-hint
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </settings-option>
</template>
