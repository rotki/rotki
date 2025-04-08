<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const zeroBased = ref<boolean>(false);
const { graphZeroBased: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(zeroBased, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <div class="pb-2">
    <SettingsOption
      #default="{ error, success, updateImmediate }"
      setting="graphZeroBased"
      frontend-setting
    >
      <RuiSwitch
        v-model="zeroBased"
        :label="t('frontend_settings.graph_basis.zero_based.label')"
        :hint="t('frontend_settings.graph_basis.zero_based.hint')"
        :success-messages="success"
        :error-messages="error"
        color="primary"
        @update:model-value="updateImmediate($event)"
      />
    </SettingsOption>
  </div>
</template>
