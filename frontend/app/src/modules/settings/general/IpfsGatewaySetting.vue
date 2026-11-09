<script setup lang="ts">
import SettingText from '@/modules/settings/controls/SettingText.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingText
    setting="ipfsGateway"
    placeholder="https://ipfs.example.com/ipfs/"
    default=""
    :label="t('general_settings.ipfs_gateway.label')"
    :hint="t('general_settings.ipfs_gateway.hint')"
    :error-message="t('general_settings.ipfs_gateway.error')"
    :success-message="t('general_settings.ipfs_gateway.success')"
  />
</template>
