<script setup lang="ts">
import { useBreakpoint } from '@rotki/ui-library';

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
            color="secondary"
            data-cy="get-premium-button"
          >
            <span v-if="!isLgAndDown">{{ t('premium_settings.get') }}</span>
            <template #append>
              <RuiIcon name="vip-crown-line" />
            </template>
          </RuiButton>
        </ExternalLink>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
