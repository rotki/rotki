<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { usePremium } from '@/composables/premium';
import ThemeManagerPlaceholder from '@/modules/theme/ThemeManagerPlaceholder.vue';
import { ThemeManager } from '@/premium/premium';

const { t } = useI18n({ useScope: 'global' });
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
        class="pt-4 "
      />
      <ThemeManagerPlaceholder
        v-else
        class="pt-4"
      />
    </SettingsItem>
  </SettingCategory>
</template>
