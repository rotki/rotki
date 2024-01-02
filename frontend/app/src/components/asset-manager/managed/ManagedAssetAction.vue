<script setup lang="ts">
const props = defineProps<{
  identifier: string;
}>();

const emit = defineEmits<{
  (e: 'toggle-whitelist'): void;
}>();

const { identifier } = toRefs(props);

const { t } = useI18n();

const { isAssetWhitelisted } = useWhitelistedAssetsStore();
const isWhitelisted = isAssetWhitelisted(identifier);

const toggleWhitelist = () => {
  emit('toggle-whitelist');
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
        <RuiButton class="!p-2" icon variant="text" v-on="on">
          <RuiIcon name="more-2-fill" size="20" />
        </RuiButton>
      </template>
      <div class="py-2 text-rui-text-secondary">
        <RuiButton
          v-if="!isWhitelisted"
          variant="list"
          @click="toggleWhitelist()"
        >
          <template #prepend>
            <RuiIcon name="checkbox-circle-line" />
          </template>
          {{ t('ignore.whitelist.action.add') }}
        </RuiButton>
        <RuiButton v-else variant="list" @click="toggleWhitelist()">
          <template #prepend>
            <RuiIcon name="close-circle-line" />
          </template>
          {{ t('ignore.whitelist.action.remove') }}
        </RuiButton>
      </div>
    </VMenu>
  </div>
</template>
