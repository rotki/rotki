<script setup lang="ts">
const { t } = useI18n();
const premium = usePremium();

const { mobile } = useDisplay();
const { href, onLinkClick } = useLinks();
</script>

<template>
  <div v-if="!premium" class="mr-2">
    <RuiTooltip :popper="{ placement: 'bottom' }" :disabled="!mobile">
      <template #activator="{ on }">
        <RuiButton
          data-cy="get-premium-button"
          color="secondary"
          :fab="mobile"
          icon
          class="py-2"
          target="_blank"
          :href="href"
          :tag="href ? 'a' : 'button'"
          v-on="on"
          @click="onLinkClick()"
        >
          <div class="flex">
            <span v-if="!mobile" class="mr-2">
              {{ t('premium_settings.get') }}
            </span>
            <RuiIcon name="vip-crown-line" />
          </div>
        </RuiButton>
      </template>
      <span>{{ t('premium_settings.get') }}</span>
    </RuiTooltip>
  </div>
</template>
