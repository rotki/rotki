<script lang="ts" setup>
withDefaults(
  defineProps<{
    premiumOnly?: boolean;
  }>(),
  { premiumOnly: false }
);

const premium = usePremium();
</script>

<template>
  <dl class="p-4 flex-1 border-default">
    <dt class="text-rui-text-secondary flex items-center gap-2">
      <slot name="title" />
    </dt>
    <dd class="text-rui-text text-h5 font-bold">
      <slot v-if="premium || !premiumOnly" />
      <PremiumLock v-else size="sm" />
    </dd>
  </dl>
</template>
