<template>
  <VMenu offset-y :close-on-content-click="false">
    <template #activator="{ on }">
      <RuiButton
        class="py-2.5 px-3"
        variant="outlined"
        data-cy="status-filter"
        v-on="on"
      >
        <RuiIcon size="20" name="equalizer-line" />
        <template #append>
          <RuiIcon size="20" name="arrow-down-s-line" />
        </template>
      </RuiButton>
    </template>
    <slot />
  </VMenu>
</template>
