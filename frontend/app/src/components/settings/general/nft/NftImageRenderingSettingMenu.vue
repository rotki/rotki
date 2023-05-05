<template>
  <v-menu offset-x left min-width="500" :close-on-content-click="false">
    <template #activator="{ on }">
      <v-btn icon v-on="on">
        <v-icon>mdi-cog</v-icon>
      </v-btn>
    </template>
    <div class="pa-4">
      <nft-image-rendering-setting />
    </div>
  </v-menu>
</template>
