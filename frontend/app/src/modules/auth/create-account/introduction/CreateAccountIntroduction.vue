<script lang="ts" setup>
import type { CreateAccountMode } from '@/modules/auth/create-account/types';

const emit = defineEmits<{
  select: [mode: CreateAccountMode];
}>();

const { t } = useI18n({ useScope: 'global' });

interface ModeCard {
  mode: CreateAccountMode;
  icon: string;
  title: string;
  description: string;
  testId: string;
}

const cards = computed<ModeCard[]>(() => [
  {
    description: t('create_account.entry.create.description'),
    icon: 'lu-user-plus',
    mode: 'create',
    testId: 'create-account-introduction-create',
    title: t('create_account.entry.create.title'),
  },
  {
    description: t('create_account.entry.restore.description'),
    icon: 'lu-cloud-download',
    mode: 'restore',
    testId: 'create-account-introduction-restore',
    title: t('create_account.entry.restore.title'),
  },
]);
</script>

<template>
  <div class="grid gap-3">
    <button
      v-for="card in cards"
      :key="card.mode"
      type="button"
      :data-testid="card.testId"
      class="flex items-start gap-4 p-4 rounded-md border text-left transition-colors bg-white dark:bg-transparent border-rui-grey-300 dark:border-rui-grey-800 hover:border-rui-primary/70 hover:bg-rui-primary/5 focus-visible:outline-2 focus-visible:outline-rui-primary"
      @click="emit('select', card.mode)"
    >
      <RuiIcon
        :name="card.icon"
        class="text-rui-primary mt-0.5 shrink-0"
      />
      <span class="flex flex-col gap-1">
        <span class="font-medium text-rui-text">
          {{ card.title }}
        </span>
        <span class="text-body-2 text-rui-text-secondary">
          {{ card.description }}
        </span>
      </span>
    </button>
  </div>
</template>
