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

const { navigation = [] } = defineProps<{
  navigation?: Nav[];
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
</script>

<template>
  <div
    class="md:flex md:flex-row-reverse md:items-start h-[calc(100vh-178px)] md:h-[calc(100vh-186px)] -mb-16 md:pt-6"
  >
    <template v-if="navigation.length > 0">
      <div
        v-if="isMdAndUp"
        class="w-[200px] lg:w-[240px] sticky top-0 bg-rui-grey-50 dark:bg-dark-surface border-default border-b-0"
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
      class="flex-1 overflow-y-auto border-default pb-8 md:pb-16 h-full flex flex-col gap-6 md:gap-8 -mx-4 px-4 md:pr-8 -mt-4 pt-4"
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
