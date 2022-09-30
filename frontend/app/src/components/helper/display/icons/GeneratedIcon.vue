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

<script setup lang="ts">
import { invertColor } from '@/utils/Color';

type Style = { [key: string]: string };
type Dimension = { value: number; unit: string };

const props = defineProps({
  size: { required: true, type: String },
  backgroundColor: { required: false, type: String, default: '#fff' },
  asset: { required: false, type: String, default: '' },
  currency: { required: false, type: Boolean, default: false }
});

const { size, backgroundColor, asset, currency } = toRefs(props);

const dimensions = computed<Dimension>(() => {
  const match: RegExpMatchArray | null = get(size).match(
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
  const { value } = get(dimensions);
  const scale = get(currency) || get(asset).length <= 2 ? 1 : 0.58;

  const lineHeight = value - 4;
  return {
    transform: `scale(${lineHeight < 20 ? 0.3 : scale})`,
    'line-height': `${lineHeight}px`
  };
});

const textColor = computed<string>(() => {
  return `#${invertColor(get(backgroundColor), true)}`;
});

const wrapperStyle = computed<Style>(() => {
  return {
    width: get(size),
    height: get(size),
    background: get(backgroundColor),
    color: get(textColor)
  };
});

const circle = computed<Style>(() => {
  return {
    width: get(size),
    height: get(size)
  };
});

const text = computed<string>(() => {
  if (get(asset).length > 3) {
    return get(asset).substr(0, 3);
  }
  return get(asset);
});
</script>
<style scoped lang="scss">
.generated-icon {
  border: 1px solid black;
  border-radius: 50%;
}
</style>
