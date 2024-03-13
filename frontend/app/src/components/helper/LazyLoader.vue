<script setup lang="ts">
withDefaults(defineProps<{
  minHeight?: string;
}>(), {
  minHeight: '16px',
});

const wrapper = ref();
const appear: Ref<boolean> = ref(false);
const height: Ref<string> = ref('auto');

useIntersectionObserver(
  wrapper,
  ([{ isIntersecting }]) => {
    set(appear, isIntersecting);
  },
);

const { height: originalHeight } = useElementBounding(wrapper);

watch(appear, (appear) => {
  if (appear)
    set(height, 'auto');
  else
    // To retain then height when the element disappear, so it doesn't break the scrolling position
    set(height, `${get(originalHeight)}px`);
});

function show() {
  set(appear, true);
}

const css = useCssModule();
</script>

<template>
  <div
    ref="wrapper"
    :class="[css.wrapper, { [css.appear]: appear }]"
    @mouseenter="!appear && show()"
  >
    <slot v-if="appear" />
  </div>
</template>

<style module lang="scss">
.wrapper {
  @apply opacity-0 transition-all;
  height: v-bind(height);
  min-height: v-bind(minHeight);

  &.appear {
    @apply opacity-100;
  }
}
</style>
