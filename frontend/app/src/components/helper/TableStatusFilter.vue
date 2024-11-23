<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});
</script>

<template>
  <RuiMenu v-bind="$attrs">
    <template #activator="{ attrs }">
      <RuiButton
        class="py-2.5 px-3 !outline-rui-grey-500 dark:!outline-rui-grey-700 !text-rui-text-secondary"
        variant="outlined"
        v-bind="{ ...attrs, 'data-cy': 'status-filter' }"
      >
        <RuiIcon
          size="20"
          name="lu-sliders-horizontal"
        />
        <template #append>
          <RuiIcon
            size="20"
            name="lu-chevron-down"
          />
        </template>
      </RuiButton>
    </template>
    <slot />
  </RuiMenu>
</template>
