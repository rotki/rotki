<script setup lang="ts">
import CardTitle from '@/components/typography/CardTitle.vue';

const expanded = ref<boolean>(true);

const panel = computed<number>(() => (get(expanded) ? 0 : -1));
</script>

<template>
  <RuiCard :content-class="!expanded ? '!py-0' : ''">
    <template #custom-header>
      <div class="flex justify-between items-center flex-wrap p-4 gap-x-4 gap-y-2">
        <CardTitle>
          <RuiButton
            variant="text"
            icon
            @click="expanded = !expanded"
          >
            <RuiIcon :name="expanded ? 'lu-square-minus' : 'lu-square-plus'" />
          </RuiButton>
          <slot name="title" />
        </CardTitle>

        <div class="flex items-center gap-2 grow justify-end">
          <slot
            v-if="expanded"
            name="details"
          />
          <slot
            v-else
            name="shortDetails"
          />
        </div>
      </div>
    </template>
    <RuiAccordions :model-value="panel">
      <RuiAccordion eager>
        <template #default>
          <slot />
        </template>
      </RuiAccordion>
    </RuiAccordions>
  </RuiCard>
</template>
