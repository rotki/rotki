<script setup lang="ts">
defineProps({
  owner: {
    required: true,
    type: String
  }
});

const { t } = useI18n();
</script>

<template>
  <VRow>
    <VCol>
      <div :class="$style.identifier">
        <slot />
      </div>
      <div class="loan-header__owner secondary--text text--lighten-2">
        {{ t('loan_header.owned_by') }}
        <HashLink :text="owner" class="d-inline font-weight-medium" />
      </div>
    </VCol>
  </VRow>
</template>

<style lang="scss" module>
.identifier {
  font-size: 24px;
  font-weight: bold;
}
</style>
