<template>
  <card outlined :class="$style.card">
    <v-row no-gutters align="center">
      <v-col cols="auto">
        <v-icon color="success">mdi-check-circle</v-icon>
      </v-col>
      <v-col>
        <div :class="$style.title" class="text--primary">
          {{ t('no_task_running.description') }}
        </div>
      </v-col>
    </v-row>
  </card>
</template>
<script setup lang="ts">
const { t } = useI18n();
</script>
<style module lang="scss">
.card {
  font-size: 16px;
  margin-left: 8px;
  margin-bottom: 8px;
}

.title {
  font-size: 1rem;
  padding-left: 1.4rem;
}
</style>
