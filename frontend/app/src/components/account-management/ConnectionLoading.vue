<template>
  <v-row
    v-if="!connected"
    no-gutters
    align="center"
    justify="center"
    class="my-3"
  >
    <v-col class="connection-loading__content grey-darken-1--text">
      <span class="connection-loading__content__text my-3 pb-6">
        {{ t('connection_loading.message') }}
      </span>
      <v-icon x-large> mdi-spin mdi-loading </v-icon>
    </v-col>
  </v-row>
</template>
<script setup lang="ts">
defineProps({
  connected: { required: true, type: Boolean }
});

const { t } = useI18n();
</script>
<style scoped lang="scss">
.connection-loading {
  &__content {
    align-items: center;
    justify-content: center;
    display: flex;
    flex-direction: column;

    &__text {
      margin-top: 48px;
      font-weight: 400;
      font-size: 26px;
    }
  }
}
</style>
