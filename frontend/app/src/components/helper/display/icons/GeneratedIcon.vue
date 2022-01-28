<template>
  <span
    :style="wrapperStyle"
    class="d-flex align-center justify-center generated-icon"
    :class="currency ? ' font-weight-medium' : 'font-weight-bold'"
  >
    <span class="d-flex align-center justify-center" :style="circle">
      <span :style="textStyle">
        {{ text }}
      </span>
    </span>
  </span>
</template>

<script lang="ts">
import { computed, defineComponent, toRefs } from '@vue/composition-api';
import { invertColor } from '@/utils/Color';

type Style = { [key: string]: string };

type Dimension = { value: number; unit: string };

export default defineComponent({
  name: 'GeneratedIcon',
  props: {
    size: { required: true, type: String },
    backgroundColor: { required: false, type: String, default: '#fff' },
    asset: { required: true, type: String },
    currency: { required: false, type: Boolean, default: false }
  },
  setup(props) {
    const { size, backgroundColor, asset, currency } = toRefs(props);

    const dimensions = computed<Dimension>(() => {
      const match: RegExpMatchArray | null = size.value.match(
        /^(\d+(?:\.\d)?)(\w+|%)?$/
      );
      const value: string = match?.[1] ?? '0';
      const unit: string = match?.[2] ?? '';
      return {
        value: Number(value),
        unit
      };
    });

    const textStyle = computed<Style>(() => {
      const { value } = dimensions.value;
      const scale = currency.value || asset.value.length <= 2 ? 1 : 0.58;

      const lineHeight = value - 4;
      return {
        transform: `scale(${lineHeight < 20 ? 0.3 : scale})`,
        'line-height': `${lineHeight}px`
      };
    });

    const textColor = computed<string>(() => {
      return `#${invertColor(backgroundColor.value, true)}`;
    });

    const wrapperStyle = computed<Style>(() => {
      return {
        width: size.value,
        height: size.value,
        background: backgroundColor.value,
        color: textColor.value
      };
    });

    const circle = computed<Style>(() => {
      return {
        width: size.value,
        height: size.value
      };
    });

    const text = computed<string>(() => {
      if (asset.value.length > 3) {
        return asset.value.substr(0, 3);
      }
      return asset.value;
    });

    return {
      wrapperStyle,
      circle,
      textStyle,
      text
    };
  }
});
</script>
<style scoped lang="scss">
.generated-icon {
  border: 1px solid black;
  border-radius: 50%;
}
</style>
