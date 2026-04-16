<script setup lang="ts">
interface Props {
  status: 'connected' | 'connecting' | 'warning' | 'disconnected';
  animate?: boolean;
}

const { status } = defineProps<Props>();

const statusConfig = computed<{ borderClass: string; bgClass: string }>(() => {
  switch (status) {
    case 'connected':
      return {
        bgClass: 'bg-rui-success-lighter',
        borderClass: 'border-rui-success-lighter/40',
      };
    case 'connecting':
      return {
        bgClass: 'bg-rui-info',
        borderClass: 'border-rui-info/40',
      };
    case 'warning':
      return {
        bgClass: 'bg-rui-warning',
        borderClass: 'border-rui-warning/40',
      };
    case 'disconnected':
    default:
      return {
        bgClass: 'bg-rui-grey-400',
        borderClass: 'border-rui-grey-400/40',
      };
  }
});
</script>

<template>
  <div :class="`p-0.5 rounded-full size-3 border ${statusConfig.borderClass}`">
    <div
      :class="`size-full rounded-full ${statusConfig.bgClass} ${animate ? 'animate-pulse' : ''}`"
    />
  </div>
</template>
