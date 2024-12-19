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
      :open-delay="400"
    >
      <template #activator>
        <ExternalLink
          custom
          premium
        >
          <RuiButton
            class="lg:!py-2 [&_span]:!hidden lg:[&_span]:!block"
            :rounded="false"
            color="primary"
            data-cy="get-premium-button"
          >
            <template #prepend>
              <RuiIcon name="vip-crown-line" />
            </template>
            {{ t('premium_settings.get') }}
          </RuiButton>
        </ExternalLink>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
