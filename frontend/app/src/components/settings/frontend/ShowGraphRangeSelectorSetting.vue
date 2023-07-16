<script setup lang="ts">
const showGraphRangeSelector = ref<boolean>(true);
const { showGraphRangeSelector: enabled } = storeToRefs(
  useFrontendSettingsStore()
);

onMounted(() => {
  set(showGraphRangeSelector, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="showGraphRangeSelector"
    frontend-setting
  >
    <VSwitch
      v-model="showGraphRangeSelector"
      class="general-settings__fields__zero-base mb-4 mt-2"
      :label="t('frontend_settings.label.show_graph_range_selector')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
