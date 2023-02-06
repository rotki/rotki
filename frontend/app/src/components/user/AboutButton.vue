<script setup lang="ts">
const { t } = useI18n();
const { showAbout } = storeToRefs(useAreaVisibilityStore());

const show = () => {
  set(showAbout, true);
};
</script>

<template>
  <v-tooltip open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-btn
        text
        fab
        depressed
        color="primary"
        v-bind="attrs"
        @click="show()"
        v-on="on"
      >
        <v-icon>mdi-information</v-icon>
      </v-btn>
    </template>
    <span>{{ t('account_management.about_tooltip') }}</span>
  </v-tooltip>
</template>
