<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string;
    locked?: boolean;
    loading?: boolean;
    protocolIcon?: string;
    bordered?: boolean;
  }>(),
  {
    title: '',
    locked: false,
    loading: false,
    protocolIcon: '',
    bordered: false
  }
);
</script>

<template>
  <RuiCard no-padding class="overflow-hidden [&>div:last-child]:h-full">
    <div class="flex p-0 h-full min-h-[130px]">
      <div v-if="bordered" class="p-2 bg-rui-grey-200 dark:bg-black">
        <AppImage
          v-if="protocolIcon"
          contain
          alt="Protocol Logo"
          size="36px"
          :src="protocolIcon"
        />
      </div>
      <div class="grow px-4 pb-4">
        <div class="flex items-center py-4">
          <CardTitle v-if="title">{{ title }}</CardTitle>
          <PremiumLock v-if="locked" class="mx-auto" />
        </div>
        <span v-if="!locked && loading">
          <RuiProgress variant="indeterminate" color="primary" />
        </span>
        <slot v-else-if="!locked" />
      </div>
    </div>
  </RuiCard>
</template>
