<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import { ThemeManager } from '@/modules/premium/premium';
import { usePremium } from '@/modules/premium/use-premium';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import ThemeManagerPlaceholder from '@/modules/shell/theme/ThemeManagerPlaceholder.vue';
defineProps<
  /* @vue-ignore */ HTMLAttributes
>();

const { t } = useI18n({ useScope: 'global' });
const premium = usePremium();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('premium_components.theme_manager.text') }}
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
