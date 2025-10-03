<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { getClass, type TabContent } from '@/types/tabs';

withDefaults(
  defineProps<{
    tabs: TabContent[];
    hideRouterView?: boolean;
    child?: boolean;
    plain?: boolean;
  }>(),
  {
    child: false,
    hideRouterView: false,
    plain: false,
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
      class="border-default"
      :class="{
        'border rounded bg-white dark:bg-rui-grey-900 flex max-w-min mx-auto mb-5': !plain,
        'border-b': plain,
      }"
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
