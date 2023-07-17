<script setup lang="ts">
const { t } = useI18n();
const { showAbout } = storeToRefs(useAreaVisibilityStore());

const show = () => {
  set(showAbout, true);
};
</script>

<template>
  <VTooltip open-delay="400" top>
    <template #activator="{ on, attrs }">
      <VBtn
        text
        fab
        depressed
        color="primary"
        v-bind="attrs"
        @click="show()"
        v-on="on"
      >
        <VIcon>mdi-information</VIcon>
      </VBtn>
    </template>
    <span>{{ t('account_management.about_tooltip') }}</span>
  </VTooltip>
</template>
