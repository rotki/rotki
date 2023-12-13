<script setup lang="ts">
const { t } = useI18n();
const premium = usePremium();
const { mobile } = useDisplay();
</script>

<template>
  <div v-if="!premium" class="mr-2">
    <RuiTooltip :popper="{ placement: 'bottom' }" :disabled="!mobile">
      <template #activator>
        <ExternalLink custom premium>
          <RuiButton
            icon
            class="lg:!py-2"
            color="secondary"
            data-cy="get-premium-button"
          >
            <span v-if="!mobile">{{ t('premium_settings.get') }}</span>
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
