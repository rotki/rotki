<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    minHeight?: string;
    initialAppear?: boolean;
  }>(),
  {
    initialAppear: false,
    minHeight: '16px',
  },
);

defineSlots<{
  default: () => any;
}>();

const { initialAppear, minHeight } = toRefs(props);

const wrapper = ref();
const appear = ref<boolean>(get(initialAppear));
const appearDebounced = refDebounced(appear, 200);
const height = ref<string>('max-content');
const usedAppear = logicAnd(appear, appearDebounced);

const visibility = useElementVisibility(wrapper);
const { height: originalHeight } = useElementBounding(wrapper);

function show() {
  set(appear, true);
}

const minHeightUsed = computed(() => {
  const heightVal = get(height);
  if (heightVal !== 'max-content' || get(usedAppear))
    return 'auto';
  return get(minHeight);
});

watch(usedAppear, (appear) => {
  if (appear)
    set(height, 'max-content');
  // To retain the height when the element disappear, so it doesn't break the scrolling position
  else set(height, `${get(originalHeight)}px`);
});

watch(visibility, (visibility) => {
  set(appear, visibility);
});
</script>

<template>
  <div
    ref="wrapper"
    :class="[$style.wrapper, { [$style.appear]: usedAppear }]"
    @mouseenter="!usedAppear && show()"
  >
    <slot v-if="usedAppear" />
  </div>
</template>

<style module lang="scss">
.wrapper {
  @apply opacity-0 transition-all;
  height: v-bind(height);
  min-height: v-bind(minHeightUsed);

  &.appear {
    @apply opacity-100;
  }
}
</style>
