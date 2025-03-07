<script setup lang="ts">
import AppImage from '@/components/common/AppImage.vue';
import CardTitle from '@/components/typography/CardTitle.vue';

withDefaults(
  defineProps<{
    title?: string;
    loading?: boolean;
    protocolIcon?: string;
    bordered?: boolean;
  }>(),
  {
    bordered: false,
    loading: false,
    protocolIcon: '',
    title: '',
  },
);
</script>

<template>
  <RuiCard
    no-padding
    class="overflow-hidden"
    content-class="h-full"
  >
    <div class="flex p-0 h-full min-h-[130px]">
      <div
        v-if="bordered"
        class="p-2 bg-rui-grey-200 dark:bg-black"
      >
        <AppImage
          v-if="protocolIcon"
          contain
          :alt="title"
          class="icon-bg"
          size="36px"
          :loading="loading"
          :src="protocolIcon"
        />
      </div>
      <div class="flex-1 px-4 pb-4">
        <div class="flex items-center py-4">
          <CardTitle v-if="title">
            {{ title }}
          </CardTitle>
        </div>
        <slot />
      </div>
    </div>
  </RuiCard>
</template>
