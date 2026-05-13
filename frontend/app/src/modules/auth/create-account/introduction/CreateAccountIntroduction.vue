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
    description: t('create_account.introduction.create.description'),
    icon: 'lu-user-plus',
    mode: 'create',
    testId: 'create-account__introduction__create',
    title: t('create_account.introduction.create.title'),
  },
  {
    description: t('create_account.introduction.restore.description'),
    icon: 'lu-cloud-download',
    mode: 'restore',
    testId: 'create-account__introduction__restore',
    title: t('create_account.introduction.restore.title'),
  },
]);
</script>

<template>
  <div class="space-y-6">
    <i18n-t
      scope="global"
      keypath="create_account.introduction.description"
      class="text-center text-rui-text-secondary whitespace-break-spaces"
      tag="div"
    >
      <template #highlight>
        <strong>{{ t('create_account.introduction.highlight') }}</strong>
      </template>
    </i18n-t>
    <div class="grid gap-3">
      <button
        v-for="card in cards"
        :key="card.mode"
        type="button"
        :data-testid="card.testId"
        class="flex items-start gap-3 p-4 rounded-md border text-left transition-colors border-rui-grey-300 dark:border-rui-grey-800 hover:border-rui-primary/70 hover:bg-rui-primary/5"
        @click="emit('select', card.mode)"
      >
        <RuiIcon
          :name="card.icon"
          class="text-rui-primary mt-0.5 shrink-0"
        />
        <div class="space-y-1">
          <div class="font-medium text-rui-text">
            {{ card.title }}
          </div>
          <div class="text-sm text-rui-text-secondary">
            {{ card.description }}
          </div>
        </div>
      </button>
    </div>
  </div>
</template>
