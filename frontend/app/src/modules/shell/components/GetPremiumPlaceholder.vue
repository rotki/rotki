<script setup lang="ts">
import GetPremiumButton from '@/modules/premium/GetPremiumButton.vue';
import { usePremiumHelper } from '@/modules/premium/use-premium-helper';
import { Routes } from '@/router/routes';

defineProps<{
  title: string;
  description?: string;
  minimumTier?: string | null;
}>();

const { t } = useI18n({ useScope: 'global' });

const { currentTier, premium } = usePremiumHelper();
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
        <i18n-t
          v-if="minimumTier && premium"
          scope="global"
          keypath="premium_placeholder.premium_description"
        >
          <template #tier>
            <strong>{{ minimumTier }}</strong>
          </template>
          <template #currentTier>
            <strong>{{ currentTier }}</strong>
          </template>
        </i18n-t>
        <i18n-t
          v-else-if="minimumTier"
          scope="global"
          keypath="premium_placeholder.free_description"
        >
          <template #tier>
            <strong>{{ minimumTier }}</strong>
          </template>
        </i18n-t>
        <template v-else>
          {{ description || t('premium_settings.chart_limit.description') }}
        </template>
      </div>
    </div>
    <div class="flex items-center gap-2 flex-wrap">
      <GetPremiumButton />
      <RouterLink :to="Routes.API_KEYS_ROTKI_PREMIUM">
        <RuiButton
          class="lg:!py-2"
        >
          <template #prepend>
            <RuiIcon name="lu-key-round" />
          </template>
          {{ t('premium_settings.actions.setup_premium_key') }}
        </RuiButton>
      </RouterLink>
    </div>
  </div>
</template>
