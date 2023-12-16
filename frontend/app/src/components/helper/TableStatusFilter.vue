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
        data-cy="status-filter"
        v-bind="attrs"
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
  </RuiMenu>
</template>
