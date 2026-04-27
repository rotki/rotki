<script setup lang="ts">
import { isSpammableAssetType } from '@/modules/assets/types';
import { useAssetsStore } from '@/modules/assets/use-assets-store';

interface AssetForIgnoreSwitch {
  identifier: string;
  assetType?: string | null;
  protocol?: string | null;
}

const { asset, loading = false, menuLoading = false } = defineProps<{
  asset: AssetForIgnoreSwitch;
  loading?: boolean;
  menuLoading?: boolean;
}>();

const emit = defineEmits<{
  'toggle-ignore': [];
  'toggle-whitelist': [];
  'toggle-spam': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { useIsAssetIgnored, useIsAssetWhitelisted } = useAssetsStore();

const identifier = computed<string>(() => asset.identifier);
const isSpam = computed<boolean>(() => asset.protocol === 'spam');
const showMoreOptions = computed<boolean>(() => isSpammableAssetType(asset.assetType));

const isIgnored = useIsAssetIgnored(identifier);
const isWhitelisted = useIsAssetWhitelisted(identifier);

const isLoading = computed<boolean>(() => loading || menuLoading);

const isIgnoringDisabled = computed<boolean>(() => get(isSpam) || get(isWhitelisted) || get(isLoading));

const tooltipMessage = computed<string>(() =>
  get(isSpam) ? t('ignore.spam.hint') : t('ignore.whitelist.hint'),
);
</script>

<template>
  <div class="flex justify-start items-center gap-2">
    <RuiTooltip
      :popper="{ placement: 'top' }"
      :open-delay="400"
      tooltip-class="max-w-[10rem]"
      :disabled="!isIgnoringDisabled || isLoading"
    >
      <template #activator>
        <RuiSwitch
          color="primary"
          hide-details
          :loading="loading"
          :disabled="isIgnoringDisabled"
          :model-value="isIgnored"
          @update:model-value="emit('toggle-ignore')"
        />
      </template>
      {{ tooltipMessage }}
    </RuiTooltip>

    <RuiMenu
      v-if="showMoreOptions"
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
            :loading="menuLoading"
            class="dark:!bg-rui-grey-800 dark:!text-white"
          >
            <RuiIcon
              name="lu-chevron-down"
              size="20"
            />
          </RuiButton>
        </RuiBadge>
      </template>
      <div class="text-rui-text-secondary">
        <RuiButton
          variant="list"
          size="sm"
          :disabled="isLoading"
          @click="emit('toggle-whitelist')"
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
          :disabled="isLoading"
          @click="emit('toggle-spam')"
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
