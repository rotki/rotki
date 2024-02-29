<template>
  <RuiMenu
    menu-class="max-w-[32rem]"
  >
    <template #activator="{ on }">
      <RuiButton
        variant="text"
        icon
        class="!p-2"
        v-on="on"
      >
        <RuiIcon name="file-settings-line" />
      </RuiButton>
    </template>
    <div class="p-4">
      <VApp>
        <NftImageRenderingSetting />
      </VApp>
    </div>
  </RuiMenu>
</template>
