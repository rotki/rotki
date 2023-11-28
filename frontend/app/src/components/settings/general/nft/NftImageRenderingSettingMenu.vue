<template>
  <VMenu offset-x left min-width="500" :close-on-content-click="false">
    <template #activator="{ on }">
      <RuiButton variant="text" icon class="!p-2" v-on="on">
        <RuiIcon name="file-settings-line" />
      </RuiButton>
    </template>
    <div class="p-4">
      <NftImageRenderingSetting />
    </div>
  </VMenu>
</template>
