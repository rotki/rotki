<template>
  <div>
    <VMenu offset-y :close-on-content-click="false">
      <template #activator="{ on }">
        <RuiButton variant="text" icon class="w-6 h-6" v-on="on">
          <RuiIcon name="arrow-down-s-line" />
        </RuiButton>
      </template>
      <slot name="refreshMenu" />
    </VMenu>
  </div>
</template>
