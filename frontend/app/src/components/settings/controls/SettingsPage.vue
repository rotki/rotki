<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(
  defineProps<{
    navigation?: Nav[];
  }>(),
  {
    navigation: () => [],
  },
);

interface Nav {
  id: string;
  label: string;
}

const parentScroller = ref<HTMLDivElement>();
const currentId = ref<string>(props.navigation[0]?.id ?? '');

function isElementInViewport(el: Element): boolean {
  const parent = get(parentScroller);
  if (!parent)
    return false;

  const parentRect = parent.getBoundingClientRect();
  const elementRect = el.getBoundingClientRect();

  return (
    elementRect.top < parentRect.bottom
    && elementRect.bottom > parentRect.top
    && elementRect.left < parentRect.right
    && elementRect.right > parentRect.left
  );
}

function checkVisibility() {
  const parent = get(parentScroller);
  if (parent && parent.scrollTop + parent.clientHeight >= parent.scrollHeight - 10) {
    // If scrolled to the bottom (with a small tolerance), set to the last navigation item's id
    set(currentId, props.navigation.at(-1)?.id ?? '');
    return;
  }

  for (const nav of props.navigation) {
    const element = document.getElementById(nav.id);
    if (element && isElementInViewport(element)) {
      set(currentId, nav.id);
      return; // Exit the function once we find the first visible element
    }
  }
  // If no element is visible, set to the first navigation item's id
  set(currentId, props.navigation[0]?.id ?? '');
}

function scrollToElement(nav: Nav) {
  const element = document.getElementById(nav.id);
  const parent = get(parentScroller);
  if (element && parent) {
    parent.scrollTo({
      top: element.offsetTop - parent.offsetTop,
      behavior: 'smooth',
    });
  }
}

onMounted(() => {
  const parent = get(parentScroller);
  if (parent) {
    parent.addEventListener('scroll', checkVisibility);
    window.addEventListener('resize', checkVisibility);
  }
  // Initial check
  checkVisibility();
});

onUnmounted(() => {
  const parent = get(parentScroller);
  if (parent) {
    parent.removeEventListener('scroll', checkVisibility);
    window.removeEventListener('resize', checkVisibility);
  }
});
</script>

<template>
  <div
    ref="parentScroller"
    class="flex items-start h-[calc(100vh-210px)] -mb-16 overflow-y-auto mt-6"
  >
    <div
      class="flex-1 pr-8 overflow-hidden border-default pb-16 min-h-full flex flex-col gap-8"
      v-bind="$attrs"
      :class="{
        'border-r': navigation.length > 0,
      }"
    >
      <slot />
    </div>
    <div
      v-if="navigation.length > 0"
      class="w-[200px] lg:w-[240px] sticky top-0"
    >
      <RuiTabs
        vertical
        color="primary"
      >
        <RuiTab
          v-for="nav in navigation"
          :key="nav.id"
          align="start"
          :active="currentId === nav.id"
          @click="scrollToElement(nav)"
        >
          {{ nav.label }}
        </RuiTab>
      </RuiTabs>
    </div>
  </div>
</template>
