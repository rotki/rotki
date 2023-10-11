<script setup lang="ts">
defineProps<{
  owner: string;
}>();

const { t } = useI18n();
</script>

<template>
  <RuiCard>
    <div class="flex flex-col">
      <div class="font-bold text-h6">
        <slot />
      </div>
      <div class="text-rui-text-secondary text-body-2">
        {{ t('loan_header.owned_by') }}
        <HashLink :text="owner" class="font-medium" />
      </div>
    </div>
  </RuiCard>
</template>
