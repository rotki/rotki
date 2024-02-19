<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <VMenu
    offset-y
    :close-on-content-click="false"
    v-bind="$attrs"
  >
    <template #activator="{ props }">
      <RuiButton
        class="py-2.5 px-3 !outline-rui-grey-500 dark:!outline-rui-grey-700 !text-rui-text-secondary"
        variant="outlined"
        data-cy="status-filter"
        v-bind="props"
      >
        <RuiIcon
          size="20"
          name="equalizer-line"
        />
        <template #append>
          <RuiIcon
            size="20"
            name="arrow-down-s-line"
          />
        </template>
      </RuiButton>
    </template>
    <slot />
  </VMenu>
</template>
