<script setup lang="ts">
import { type TabContent, getClass } from '@/types/tabs';

withDefaults(defineProps<{
  tabs: TabContent[];
  hideRouterView?: boolean;
  child?: boolean;
}>(), {
  hideRouterView: false,
  child: false,
});

const model = ref('');
</script>

<template>
  <div :class="{ container: !child }">
    <RuiTabs
      v-model="model"
      color="primary"
      class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min mb-5 mx-auto"
    >
      <template #default>
        <RuiTab
          v-for="tab in tabs"
          :key="tab.route"
          :value="tab.route"
          link
          :to="tab.route"
          :exact-path="false"
          :class="getClass(tab.route)"
        >
          <template #prepend>
            <RuiIcon
              size="20"
              :name="tab.icon"
            />
          </template>
          {{ tab.text }}
        </RuiTab>
      </template>
    </RuiTabs>
    <RouterView v-if="!hideRouterView" />
  </div>
</template>
