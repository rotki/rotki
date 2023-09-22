<script setup lang="ts">
defineProps({
  tooltip: { required: true, type: String, default: '' },
  onMenu: { required: false, type: Object, default: () => {} },
  retainFocusOnClick: { required: false, type: Boolean, default: false },
  className: { required: false, type: String, default: '' }
});

const emit = defineEmits(['click']);
const click = () => emit('click');
</script>

<template>
  <VTooltip bottom z-index="215" class="block" open-delay="250">
    <template #activator="{ on: menu }">
      <RuiButton
        icon
        variant="text"
        :class="className"
        class="!w-12 !h-12"
        :retain-focus-on-click="retainFocusOnClick"
        @click="click()"
        v-on="{ ...menu, ...onMenu }"
      >
        <slot />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </VTooltip>
</template>
