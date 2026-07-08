<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';

const enableAliasNames = ref<boolean>(true);
const enabled = useSetting('enableAliasNames');

onMounted(() => {
  set(enableAliasNames, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="enableAliasNames"
    :error-message="t('frontend_settings.alias_names.validation.error')"
  >
    <RuiSwitch
      v-model="enableAliasNames"
      class="mt-4"
      :label="t('frontend_settings.alias_names.label')"
      :messages="success"
      :error-messages="error"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
