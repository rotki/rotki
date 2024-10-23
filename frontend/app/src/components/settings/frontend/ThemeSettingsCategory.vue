<script setup lang="ts">
import { ThemeManager } from '@/premium/premium';
import { usePremium } from '@/composables/premium';

const { t } = useI18n();
const premium = usePremium();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('premium_components.theme_manager.text') }}
    </template>
    <template #subtitle>
      {{ t('premium_components.theme_manager.text_hint') }}
    </template>
    <SettingsItem>
      <ThemeManager
        v-if="premium"
        class="pt-4"
      />
      <ThemeManagerLock
        v-else
        class="pt-4"
      />
    </SettingsItem>
  </SettingCategory>
</template>
