<script setup lang="ts">
defineProps<{
  items: any[];
  getKey: (item: any) => string;
  showTooltip?: (item: any) => boolean;
}>();

const { t } = useI18n();
const css = useCssModule();
</script>

<template>
  <VDialog width="1200">
    <template #activator="{ on }">
      <VBtn text class="ml-4" v-on="on">
        {{ t('common.details') }}
        <VIcon small>mdi-chevron-right</VIcon>
      </VBtn>
    </template>
    <template #default="dialog">
      <VCard :class="css.card">
        <VCardTitle class="flex justify-between pb-0">
          <div>
            <slot name="title" />
          </div>
          <VBtn icon @click="dialog.value = false">
            <VIcon>mdi-close</VIcon>
          </VBtn>
        </VCardTitle>

        <slot name="current" />

        <div class="px-6 pb-4">
          <div v-for="item in items" :key="getKey(item)" :class="css.item">
            <div class="flex items-center">
              <slot name="item" :item="item" />

              <VTooltip v-if="showTooltip ? showTooltip(item) : true" bottom>
                <template #activator="{ on }">
                  <VIcon class="ml-2" v-on="on"> mdi-help-circle </VIcon>
                </template>

                <slot name="tooltip" :item="item" />
              </VTooltip>
            </div>
            <slot name="steps" :item="item" />
          </div>
        </div>
      </VCard>
    </template>
  </VDialog>
</template>

<style module lang="scss">
.item {
  padding: 1rem 0;
  border-top: 1px solid var(--v-rotki-light-grey-darken1);
}

.card {
  width: 100%;
  overflow: auto;
}
</style>
