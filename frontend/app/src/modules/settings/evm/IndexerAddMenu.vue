<script setup lang="ts">
import type { PrioritizedListItemData } from '@/modules/settings/types/prioritized-list-data';
import type { PrioritizedListId } from '@/modules/settings/types/prioritized-list-id';
import PrioritizedListEntry from '@/modules/shell/components/PrioritizedListEntry.vue';

/** Adds an indexer to the open scope's order, from the editor footer so the list above never moves. */
defineProps<{
  items: PrioritizedListItemData<PrioritizedListId>[];
}>();

const emit = defineEmits<{
  add: [indexer: PrioritizedListId];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiMenu
    :options="{ placement: 'top-start' }"
    close-on-content-click
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="outlined"
        color="primary"
        v-bind="attrs"
        data-testid="add-indexer"
      >
        <template #prepend>
          <RuiIcon
            name="lu-plus"
            size="16"
          />
        </template>
        {{ t('evm_settings.indexer.add_indexer') }}
      </RuiButton>
    </template>
    <div class="py-1">
      <RuiButton
        v-for="item in items"
        :key="item.identifier"
        variant="list"
        class="w-full"
        data-testid="add-indexer-item"
        :data-key="item.identifier"
        @click="emit('add', item.identifier)"
      >
        <PrioritizedListEntry
          :data="item"
          size="20px"
          class="gap-2!"
        />
      </RuiButton>
    </div>
  </RuiMenu>
</template>
