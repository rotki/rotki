<script setup lang="ts">
import { useSettingsPageHighlight } from '@/modules/settings/use-settings-page-highlight';
import { useSettingsScrollSpy } from '@/modules/settings/use-settings-scroll-spy';

interface Nav {
  id: string;
  label: string;
}

defineOptions({
  inheritAttrs: false,
});

const { navigation = [], fillsHeight = false } = defineProps<{
  navigation?: Nav[];
  /**
   * From md up the page fills the scroller and scrolls inside its own areas, so the scroller keeps
   * a fixed bottom margin instead of growing with the task dock, which would squeeze the page. The
   * page pads the areas the dock covers itself.
   */
  fillsHeight?: boolean;
}>();

defineSlots<{
  default: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const parentScroller = useTemplateRef<HTMLDivElement>('parentScroller');

const { isMdAndUp } = useBreakpoint();

const { currentId, isElementInViewport, scrollToElement } = useSettingsScrollSpy({
  navigation,
  scroller: parentScroller,
});

useSettingsPageHighlight({ scrollToElement, isElementInViewport });

/**
 * A page with one section has nothing to jump between, so it keeps the rail's width, which holds
 * the content as wide as on the other tabs, but none of its contents.
 */
const showRail = computed<boolean>(() => navigation.length > 1);
</script>

<template>
  <div
    class="md:flex md:flex-row-reverse md:items-start h-[calc(100vh-178px)] md:h-[calc(100vh-173px)] -mb-16 md:pt-6"
  >
    <div
      v-if="navigation.length === 1"
      class="hidden md:block w-[200px] lg:w-[240px]"
    />
    <template v-else-if="showRail">
      <div
        v-if="isMdAndUp"
        class="w-[200px] lg:w-[240px] sticky top-0 bg-rui-grey-50 dark:bg-rui-background border-default border-b-0"
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
      class="flex-1 overflow-y-auto [scrollbar-gutter:stable] border-default h-full flex flex-col gap-6 md:gap-8 -mx-4 px-4 md:pr-8 -mt-4 pt-4 pb-[max(2rem,var(--rotki-dock-inset,0px))]"
      v-bind="$attrs"
      :class="{
        'md:pb-4': fillsHeight,
        'md:pb-[max(4rem,var(--rotki-dock-inset,0px))]': !fillsHeight,
        'md:border-r h-[calc(100%-72px)]! md:h-full! md:mr-0': showRail,
        'pt-6 md:pt-0 md:mr-0': navigation.length === 1,
        'md:-mr-8! pt-6 md:pt-0': navigation.length === 0,
      }"
    >
      <slot />
    </div>
  </div>
</template>
