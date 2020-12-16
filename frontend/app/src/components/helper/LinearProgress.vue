<template>
  <div class="linear-progress d-flex" :style="style" />
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class LinearProgress extends Vue {
  @Prop({ required: false, type: String, default: '3px' })
  height!: string;
  @Prop({ required: false, type: Boolean, default: false })
  datatable!: boolean;

  get style() {
    const opacity = Math.round(255 * 0.3).toString(16);
    const theme = this.$vuetify.theme;
    const primaryColor = theme.currentTheme['primary'] ?? '#000000';
    const background = `#${primaryColor.toString().replace('#', '')}${opacity}`;
    const extra = this.datatable
      ? {
          width: 'calc(100% + 32px)',
          'margin-left': '-16px'
        }
      : {};
    return {
      height: this.height,
      background,
      ...extra
    };
  }
}
</script>

<style scoped lang="scss">
.base-progress {
  width: 100%;
  margin: 0;
  will-change: left, right;
}

.linear-progress {
  &:before {
    background-color: var(--v-primary-base);
    content: '';
    -webkit-animation: progress 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    animation: progress 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;

    @extend .base-progress;
  }

  @extend .base-progress;
}
@keyframes progress {
  0% {
    margin-left: 0;
    margin-right: 100%;
  }

  50% {
    margin-left: 25%;
    margin-right: 0;
  }

  100% {
    margin-left: 100%;
    margin-right: 0;
  }
}
</style>
