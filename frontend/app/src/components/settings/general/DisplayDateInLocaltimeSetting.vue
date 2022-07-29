<template>
  <settings-option
    #default="{ error, success, update }"
    setting="displayDateInLocaltime"
    :error-message="
      $tc('general_settings.validation.display_date_in_localtime.error')
    "
  >
    <v-switch
      v-model="displayDateInLocaltime"
      class="general-settings__fields__display-date-in-localtime mb-4 mt-0"
      color="primary"
      :label="$t('general_settings.labels.display_date_in_localtime')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';

const displayDateInLocaltime = ref<boolean>(true);
const { generalSettings } = useSettings();

onMounted(() => {
  const settings = get(generalSettings);
  set(displayDateInLocaltime, settings.displayDateInLocaltime);
});
</script>
