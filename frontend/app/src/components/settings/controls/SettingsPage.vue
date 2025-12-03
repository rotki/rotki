<script setup lang="ts">
interface Nav {
  id: string;
  label: string;
}

defineOptions({
  inheritAttrs: false,
});

const props = withDefaults(defineProps<{
  navigation?: Nav[];
}>(), {
  navigation: () => [],
});

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const parentScroller = ref<HTMLDivElement>();
const currentId = ref<string>(props.navigation[0]?.id ?? '');

const { isMdAndUp } = useBreakpoint();

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
  if (parent) {
    if (parent.scrollTop === 0) {
      set(currentId, props.navigation.at(0)?.id ?? '');
      return;
    }
    if (parent.scrollTop + parent.clientHeight >= parent.scrollHeight - 10) {
      // If scrolled to the bottom (with a small tolerance), set to the last navigation item's id
      set(currentId, props.navigation.at(-1)?.id ?? '');
      return;
    }
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

function scrollToElement(navId?: string) {
  if (!navId)
    return;

  const element = document.getElementById(navId);
  const parent = get(parentScroller);
  if (element && parent) {
    parent.scrollTo({
      behavior: 'smooth',
      top: element.offsetTop - parent.offsetTop,
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
    class="md:flex md:flex-row-reverse md:items-start h-[calc(100vh-178px)] md:h-[calc(100vh-186px)] -mb-16 md:pt-6"
  >
    <template v-if="navigation.length > 0">
      <div
        v-if="isMdAndUp"
        class="w-[200px] lg:w-[240px] sticky top-0 bg-rui-grey-50 dark:bg-[#121212] border-default border-b-0"
      >
        <RuiTabs
          :vertical="isMdAndUp"
          :indicator-position="isMdAndUp ? 'start' : 'end'"
          color="primary"
        >
          <RuiTab
            v-for="nav in navigation"
            :key="nav.id"
            align="start"
            :active="currentId === nav.id"
            @click="scrollToElement(nav.id)"
          >
            {{ nav.label }}
          </RuiTab>
        </RuiTabs>
      </div>
      <RuiMenuSelect
        v-else
        :model-value="currentId"
        :options="navigation"
        variant="outlined"
        key-attr="id"
        text-attr="label"
        :label="t('settings.go_to_section')"
        class="py-4"
        hide-details
        dense
        @update:model-value="scrollToElement($event)"
      />
    </template>
    <div
      ref="parentScroller"
      class="flex-1 overflow-y-auto border-default pb-8 md:pb-16 h-full flex flex-col gap-6 md:gap-8 -mr-4 pr-4 md:pr-8"
      v-bind="$attrs"
      :class="{
        'md:border-r !h-[calc(100%-72px)] md:!h-full md:mr-0': navigation.length > 0,
        'md:!-mr-8 pt-6 md:pt-0': navigation.length === 0,
      }"
    >
      <slot />
    </div>
  </div>
</template>
