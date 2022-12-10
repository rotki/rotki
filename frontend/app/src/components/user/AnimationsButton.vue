<template>
  <v-tooltip open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-btn
        text
        fab
        depressed
        color="primary"
        v-bind="attrs"
        v-on="on"
        @click="toggleAnimation"
      >
        <v-icon v-if="animationEnabled">mdi-pause</v-icon>
        <v-icon v-else>mdi-play</v-icon>
      </v-btn>
    </template>
    <span v-if="animationEnabled">
      {{ t('frontend_settings.animations.disable') }} ({{
        t('frontend_settings.animations.disable_hint')
      }})
    </span>
    <span v-else>{{ t('frontend_settings.animations.enable') }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
const { t } = useI18n();
const { animationEnabled, toggleAnimation } = useAnimation();
</script>
