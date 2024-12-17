<script setup lang="ts">
import { usePremium } from '@/composables/premium';
import ExternalLink from '@/components/helper/ExternalLink.vue';

const { t } = useI18n();
const premium = usePremium();
const { isLgAndDown } = useBreakpoint();
</script>

<template>
  <div
    v-if="!premium"
    class="mr-2"
  >
    <RuiTooltip
      :popper="{ placement: 'bottom' }"
      :disabled="!isLgAndDown"
    >
      <template #activator>
        <ExternalLink
          custom
          premium
        >
          <RuiButton
            icon
            class="lg:!py-2"
            :rounded="false"
            color="primary"
            data-cy="get-premium-button"
          >
            <span v-if="!isLgAndDown">{{ t('premium_settings.get') }}</span>
            <template #prepend>
              <RuiIcon name="vip-crown-line" />
            </template>
          </RuiButton>
        </ExternalLink>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
