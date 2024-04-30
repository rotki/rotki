<script setup lang="ts">
const props = withDefaults(defineProps<{
  minHeight?: string;
  initialAppear?: boolean;
}>(), {
  minHeight: '16px',
  initialAppear: false,
});

const { minHeight, initialAppear } = toRefs(props);

const wrapper = ref();
const appear: Ref<boolean> = ref(get(initialAppear));
const appearDebounced = refDebounced(appear, 200);
const height: Ref<string> = ref('max-content');
const usedAppear = logicAnd(appear, appearDebounced);

useIntersectionObserver(
  wrapper,
  ([{ intersectionRect, isIntersecting }]) => {
    set(appear, intersectionRect.height > 0 || isIntersecting);
  },
  {
    threshold: 0,
  },
);

const { height: originalHeight } = useElementBounding(wrapper);

watch(usedAppear, (appear) => {
  if (appear)
    set(height, 'max-content');
  else
    // To retain then height when the element disappear, so it doesn't break the scrolling position
    set(height, `${get(originalHeight)}px`);
});

function show() {
  set(appear, true);
}

const css = useCssModule();

const minHeightUsed = computed(() => {
  const heightVal = get(height);
  if (heightVal !== 'max-content')
    return 'auto';
  return get(minHeight);
});
</script>

<template>
  <div
    ref="wrapper"
    :class="[css.wrapper, { [css.appear]: usedAppear }]"
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
