<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    identifier: string;
    isSpam?: boolean;
  }>(),
  {
    isSpam: false
  }
);

const emit = defineEmits<{
  (e: 'toggle-whitelist'): void;
  (e: 'toggle-spam'): void;
}>();

const { identifier } = toRefs(props);

const { t } = useI18n();

const { isAssetWhitelisted } = useWhitelistedAssetsStore();
const isWhitelisted = isAssetWhitelisted(identifier);

const toggleWhitelist = () => {
  emit('toggle-whitelist');
};

const toggleSpam = () => {
  emit('toggle-spam');
};
</script>

<template>
  <div class="flex items-center">
    <VMenu
      max-width="250px"
      min-width="200px"
      left
      offset-y
      transition="slide-y-transition"
    >
      <template #activator="{ on }">
        <RuiButton class="!p-1" icon variant="text" v-on="on">
          <RuiIcon name="arrow-down-s-line" size="20" />
        </RuiButton>
      </template>
      <div class="py-2 text-rui-text-secondary">
        <RuiButton variant="list" @click="toggleWhitelist()">
          <template #prepend>
            <RuiCheckbox
              color="primary"
              class="[&_span]:-mr-1 [&_span]:!py-0"
              hide-details
              :value="isWhitelisted"
            />
          </template>
          {{ t('ignore.whitelist.action.add') }}
        </RuiButton>
        <RuiButton variant="list" @click="toggleSpam()">
          <template #prepend>
            <RuiCheckbox
              color="primary"
              class="[&_span]:-mr-1 [&_span]:!py-0"
              hide-details
              :value="isSpam"
            />
          </template>
          {{ t('ignore.spam.action.add') }}
        </RuiButton>
      </div>
    </VMenu>
  </div>
</template>
