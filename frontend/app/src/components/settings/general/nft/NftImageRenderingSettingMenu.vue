<template>
  <VMenu offset-x left min-width="500" :close-on-content-click="false">
    <template #activator="{ on }">
      <RuiButton icon variant="text" v-on="on">
        <VIcon>mdi-cog</VIcon>
      </RuiButton>
    </template>
    <div class="pa-4">
      <NftImageRenderingSetting />
    </div>
  </VMenu>
</template>
