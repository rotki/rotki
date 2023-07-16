<script setup lang="ts">
const { t } = useI18n();
const { animationEnabled, toggleAnimation } = useAnimation();
</script>

<template>
  <VTooltip open-delay="400" top>
    <template #activator="{ on, attrs }">
      <VBtn
        text
        fab
        depressed
        color="primary"
        v-bind="attrs"
        v-on="on"
        @click="toggleAnimation()"
      >
        <VIcon v-if="animationEnabled">mdi-pause</VIcon>
        <VIcon v-else>mdi-play</VIcon>
      </VBtn>
    </template>
    <span v-if="animationEnabled">
      {{ t('frontend_settings.animations.disable') }} ({{
        t('frontend_settings.animations.disable_hint')
      }})
    </span>
    <span v-else>{{ t('frontend_settings.animations.enable') }}</span>
  </VTooltip>
</template>
