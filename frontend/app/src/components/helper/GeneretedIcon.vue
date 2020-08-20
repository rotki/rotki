<template>
  <span
    :style="wrapperStyle"
    class="d-flex align-center justify-center generated-icon"
    :class="currency ? ' font-weight-medium' : 'font-weight-bold'"
  >
    <span>
      <span :style="textStyle">
        {{ text }}
      </span>
    </span>
  </span>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { invertColor } from '@/utils/Color';

type Style = { [key: string]: string };

type Dimension = { value: number; unit: string };
@Component({})
export default class GeneretedIcon extends Vue {
  @Prop({ required: true })
  size!: string;
  @Prop({ required: false, default: '#7e7d7c' })
  backgroundColor!: string;
  @Prop({ required: true })
  asset!: string;
  @Prop({ required: false, type: Boolean, default: false })
  currency!: boolean;

  get textStyle(): Style {
    const { value, unit } = this.dimensions;
    const fontSize = this.currency
      ? value * 0.65
      : (value * 0.9) / this.text.length;
    return {
      'font-size': `${fontSize}${unit}`,
      'line-height': this.size
    };
  }

  get wrapperStyle(): Style {
    return {
      width: this.size,
      height: this.size,
      background: this.backgroundColor,
      color: this.textColor
    };
  }

  get text(): string {
    if (this.asset.length > 3) {
      return this.asset.substr(0, 3);
    }
    return this.asset;
  }

  get textColor(): string {
    return `#${invertColor(this.backgroundColor, true)}`;
  }

  get dimensions(): Dimension {
    const match = this.size.match(/^(\d+(?:\.\d)?)(\w+|%)?$/);
    const size = match?.[1] ?? '0';
    const unit = match?.[2] ?? '';
    return {
      value: Number(size),
      unit
    };
  }
}
</script>
<style scoped lang="scss">
.generated-icon {
  border-radius: 50%;
  display: inline-block;
}
</style>
