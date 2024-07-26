<script setup lang="ts">
import { type TabContent, getClass } from '@/types/tabs';
import type { RouteLocationRaw } from 'vue-router';

withDefaults(
  defineProps<{
    tabs: TabContent[];
    hideRouterView?: boolean;
    child?: boolean;
  }>(),
  {
    hideRouterView: false,
    child: false,
  },
);

const model = ref('');

const router = useRouter();

function getTabClass(route: RouteLocationRaw): string {
  return getClass(router.resolve(route).path);
}
</script>

<template>
  <div :class="{ container: !child }">
    <RuiTabs
      v-model="model"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-5 mx-auto"
    >
      <RuiTab
        v-for="tab in tabs"
        :key="tab.route.toString()"
        :model-value="tab.route"
        link
        :to="tab.route"
        :exact-path="false"
        :class="getTabClass(tab.route)"
      >
        <template #prepend>
          <RuiIcon
            size="20"
            :name="tab.icon"
          />
        </template>
        {{ tab.text }}
      </RuiTab>
    </RuiTabs>
    <RouterView v-if="!hideRouterView" />
  </div>
</template>
