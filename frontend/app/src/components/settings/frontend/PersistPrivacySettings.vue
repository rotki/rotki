<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const { persistPrivacySettings } = storeToRefs(useFrontendSettingsStore());

const persistPrivacy = ref<boolean>(false);

const { t } = useI18n({ useScope: 'global' });

function setData() {
  set(persistPrivacy, get(persistPrivacySettings));
}

onMounted(setData);

watch(persistPrivacySettings, setData);
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('frontend_settings.persist_privacy.title') }}
    </template>

    <SettingsOption
      #default="{ error, success, updateImmediate }"
      setting="persistPrivacySettings"
      frontend-setting
      :error-message="t('frontend_settings.persist_privacy.validation.error')"
    >
      <RuiSwitch
        v-model="persistPrivacy"
        color="primary"
        class="my-2"
        :label="t('frontend_settings.persist_privacy.label')"
        :hint="t('frontend_settings.persist_privacy.hint')"
        :success-messages="success"
        :error-messages="error"
        @update:model-value="updateImmediate($event)"
      />
    </SettingsOption>
  </SettingsItem>
</template>
