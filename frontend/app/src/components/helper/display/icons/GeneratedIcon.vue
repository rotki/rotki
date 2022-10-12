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

const textStyle = computed<Style>(() => {
  const length = get(text).length;
  const { value } = get(dimensions);

  const fontSize = value / length + (length - 3) * 5;

  return {
    fontSize: `${fontSize}px`
  };
});

const textColor = computed<string>(() => {
  return `#${invertColor(get(backgroundColor), true)}`;
});
</script>
<style scoped lang="scss">
.generated-icon {
  border: 1px solid black;
  border-radius: 50%;
  white-space: nowrap;
}
</style>
