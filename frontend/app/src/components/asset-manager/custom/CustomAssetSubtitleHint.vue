<script setup lang="ts">
const { t } = useI18n();

const visible = ref(false);
</script>

<template>
  <VMenu v-model="visible" offset-x>
    <template #activator="{ on }">
      <RuiButton variant="text" icon @click="visible = true" v-on="on">
        <RuiIcon name="question-line" />
      </RuiButton>
    </template>
    <div class="pa-4">
      {{ t('asset_table.custom.subtitle') }}
    </div>
  </VMenu>
</template>
