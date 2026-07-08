<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';

const zeroBased = ref<boolean>(false);
const enabled = useSetting('graphZeroBased');

onMounted(() => {
  set(zeroBased, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="pb-2">
    <SettingsOption
      #default="{ error, success, updateImmediate }"
      setting="graphZeroBased"
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
