<script setup lang="ts">
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';

const props = withDefaults(
  defineProps<{
    identifier: string;
    isSpam?: boolean;
  }>(),
  {
    isSpam: false,
  },
);

const emit = defineEmits<{
  (e: 'toggle-whitelist'): void;
  (e: 'toggle-spam'): void;
}>();

const { identifier } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const { isAssetWhitelisted } = useWhitelistedAssetsStore();
const isWhitelisted = isAssetWhitelisted(identifier);

function toggleWhitelist() {
  emit('toggle-whitelist');
}

function toggleSpam() {
  emit('toggle-spam');
}
</script>

<template>
  <div class="flex items-center">
    <RuiMenu
      menu-class="w-[15rem]"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiBadge
          :model-value="isWhitelisted || isSpam"
          color="primary"
          dot
          placement="top"
          offset-y="12"
          offset-x="-10"
          size="md"
          class="flex items-center"
        >
          <RuiButton
            icon
            v-bind="attrs"
            size="sm"
            class="dark:!bg-rui-grey-800 dark:!text-white"
          >
            <RuiIcon
              name="lu-chevron-down"
              size="20"
            />
          </RuiButton>
        </RuiBadge>
      </template>
      <div class="py-2 text-rui-text-secondary">
        <RuiButton
          variant="list"
          size="sm"
          @click="toggleWhitelist()"
        >
          <template #prepend>
            <RuiCheckbox
              class="-mr-2"
              color="primary"
              hide-details
              :model-value="isWhitelisted"
            />
          </template>
          {{ t('ignore.whitelist.action.add') }}
        </RuiButton>
        <RuiButton
          variant="list"
          size="sm"
          @click="toggleSpam()"
        >
          <template #prepend>
            <RuiCheckbox
              class="-mr-2"
              color="primary"
              hide-details
              :model-value="isSpam"
            />
          </template>
          {{ t('ignore.spam.action.add') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
