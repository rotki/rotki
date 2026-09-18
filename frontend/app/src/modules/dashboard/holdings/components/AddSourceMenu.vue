<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { useAddSourceOptions } from '@/modules/dashboard/holdings/use-add-source-options';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();

const options = useAddSourceOptions();

async function add(to: RouteLocationRaw): Promise<void> {
  await router.push(to);
}
</script>

<template>
  <RuiMenu
    :options="{ placement: 'bottom-start' }"
    :class-names="{ wrapper: 'w-full' }"
  >
    <template #activator="{ attrs }">
      <button
        type="button"
        class="grid grid-cols-[10px_1fr] items-center gap-2.5 w-full px-1.5 py-1 rounded text-left text-sm text-rui-primary hover:bg-rui-primary/10"
        data-testid="dashboard-add-source"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-plus"
          size="14"
          class="-ml-0.5"
        />
        <span class="flex items-center gap-1 font-medium">
          {{ t('dashboard.holdings.add.title') }}
          <RuiIcon
            name="lu-chevron-down"
            size="14"
          />
        </span>
      </button>
    </template>
    <div class="py-2">
      <RuiButton
        v-for="option in options"
        :key="option.key"
        variant="list"
        :data-testid="`dashboard-add-source-${option.key}`"
        @click="add(option.to)"
      >
        <template #prepend>
          <RuiIcon :name="option.icon" />
        </template>
        {{ option.label }}
      </RuiButton>
    </div>
  </RuiMenu>
</template>
