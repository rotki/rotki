<script setup lang="ts">
const { t } = useI18n();
const premium = usePremium();
const { mobile } = useDisplay();
</script>

<template>
  <div v-if="!premium" class="mr-2">
    <RuiTooltip :popper="{ placement: 'bottom' }" :disabled="!mobile">
      <template #activator>
        <ExternalLinkButton
          data-cy="get-premium-button"
          color="secondary"
          :fab="mobile"
          icon
          class="py-2"
        >
          <span v-if="!mobile">{{ t('premium_settings.get') }}</span>
          <template #append>
            <RuiIcon name="vip-crown-line" />
          </template>
        </ExternalLinkButton>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
