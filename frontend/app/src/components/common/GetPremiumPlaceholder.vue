<script setup lang="ts">
import GetPremiumButton from '@/components/premium/GetPremiumButton.vue';

defineProps<{
  title: string;
  description?: string;
}>();

const { t } = useI18n();
</script>

<template>
  <div class="flex flex-col items-center justify-center text-center">
    <div class="size-12 rounded-full border border-rui-primary-lighter flex items-center justify-center mb-4">
      <div class="size-8 rounded-full bg-rui-primary text-white flex items-center justify-center">
        <RuiIcon
          name="lu-lock-keyhole"
          size="20"
        />
      </div>
    </div>
    <div class="pb-6">
      <div class="text-h6 !leading-7 mb-1">
        {{ title }}
      </div>
      <div class="text-rui-text-secondary">
        {{ description || t('premium_settings.chart_limit.description') }}
      </div>
    </div>
    <GetPremiumButton />
  </div>
</template>
