<script setup lang="ts">
import { ThemeManager } from '@/modules/premium/premium';
import { usePremium } from '@/modules/premium/use-premium';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import ThemeManagerPlaceholder from '@/modules/shell/theme/ThemeManagerPlaceholder.vue';

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
