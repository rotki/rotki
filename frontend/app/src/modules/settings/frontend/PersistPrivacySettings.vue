<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';

const persistPrivacySettings = useSetting('persistPrivacySettings');

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
