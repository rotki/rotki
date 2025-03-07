<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const showGraphRangeSelector = ref<boolean>(true);
const { showGraphRangeSelector: enabled } = storeToRefs(useFrontendSettingsStore());

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
    <RuiSwitch
      v-model="showGraphRangeSelector"
      :label="t('frontend_settings.graph_basis.range_selector.label')"
      :success-messages="success"
      :error-messages="error"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
