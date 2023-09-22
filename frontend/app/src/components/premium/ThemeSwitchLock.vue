<script setup lang="ts">
const { href, onLinkClick } = useLinks();
const { t } = useI18n();
</script>

<template>
  <VTooltip bottom>
    <template #activator="{ on }">
      <VBadge color="transparent" offset-y="20" offset-x="20">
        <RuiButton
          variant="text"
          icon
          target="_blank"
          class="secondary--text text--lighten-4"
          :href="href"
          v-on="on"
          @click="onLinkClick()"
        >
          <VIcon>mdi-white-balance-sunny</VIcon>
        </RuiButton>
        <template #badge>
          <VIcon color="primary" small>mdi-lock</VIcon>
        </template>
      </VBadge>
    </template>
    <span>
      {{ t('theme_switch_lock.tooltip') }}
    </span>
  </VTooltip>
</template>
