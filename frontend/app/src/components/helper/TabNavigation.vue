<script setup lang="ts">
import { type TabContent, getClass } from '@/types/tabs';

defineProps<{
  tabs: TabContent[];
}>();

const model = ref('');
</script>

<template>
  <div class="container">
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
          :class="getClass(tab.route)"
        >
          <template #prepend>
            <RuiIcon size="20" :name="tab.icon" />
          </template>
          {{ tab.text }}
        </RuiTab>
      </template>
    </RuiTabs>
    <RouterView />
  </div>
</template>
