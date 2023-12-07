<script setup lang="ts">
defineProps<{
  items: any[];
  getKey: (item: any) => string;
  showTooltip?: (item: any) => boolean;
}>();

const { t } = useI18n();
</script>

<template>
  <VDialog width="1200">
    <template #activator="{ on }">
      <RuiButton variant="text" class="ml-4" v-on="on">
        {{ t('common.details') }}
        <template #append>
          <RuiIcon name="arrow-right-s-line" />
        </template>
      </RuiButton>
    </template>
    <template #default="dialog">
      <RuiCard>
        <template #custom-header>
          <div class="flex justify-between gap-4 p-4 pb-0 items-start">
            <div>
              <h5 class="text-h5">
                <slot name="title" />
              </h5>
              <div class="text-caption">
                <slot name="current" />
              </div>
            </div>
            <RuiButton icon variant="text" @click="dialog.value = false">
              <RuiIcon name="close-line" />
            </RuiButton>
          </div>
        </template>

        <div>
          <div
            v-for="item in items"
            :key="getKey(item)"
            class="border-t border-default py-3"
          >
            <div class="flex items-center">
              <slot name="item" :item="item" />

              <RuiTooltip
                v-if="showTooltip ? showTooltip(item) : true"
                class="cursor-pointer"
                :open-delay="400"
                tooltip-class="max-w-[12rem]"
              >
                <template #activator>
                  <RuiIcon
                    class="ml-2 text-rui-text-secondary"
                    name="question-line"
                  />
                </template>

                <slot name="tooltip" :item="item" />
              </RuiTooltip>
            </div>
            <slot name="steps" :item="item" />
          </div>
        </div>
      </RuiCard>
    </template>
  </VDialog>
</template>
