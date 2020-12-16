<template>
  <div class="circular-progress d-flex justify-center align-center">
    <div class="circular-progress__progress" :style="style" />
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class CirclularProgress extends Vue {
  @Prop({ required: false, type: String, default: '48px' })
  size!: string;

  get background(): string {
    const opacity = Math.round(255 * 0.3).toString(16);
    const theme = this.$vuetify.theme;
    const primaryColor = theme.currentTheme['primary'] ?? '#000000';
    return `#${primaryColor.toString().replace('#', '')}${opacity}`;
  }

  get style() {
    return {
      width: this.size,
      height: this.size
    };
  }
}
</script>

<style scoped lang="scss">
.circular-progress {
  &__progress {
    border-right: solid transparent;
    border-top: solid var(--v-primary-base);
    border-left: solid var(--v-primary-base);
    border-bottom: solid var(--v-primary-base);
    border-radius: 50%;
    border-width: 4px;
    animation: rotating 1.5s linear infinite;
    will-change: transform;
  }
}
@keyframes rotating {
  0% {
    transform: rotate(0deg);
  }

  60% {
    transform: rotate(270deg);
  }

  100% {
    transform: rotate(360deg);
  }
}
</style>
