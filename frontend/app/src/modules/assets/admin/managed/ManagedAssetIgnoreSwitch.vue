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
      :options="{ placement: 'top' }"
      :open-delay="400"
      :class-names="{ tooltip: 'max-w-40' }"
      :disabled="!isIgnoringDisabled || isLoading"
    >
      <template #activator>
        <RuiSwitch
          color="primary"
          details="hidden"
          :loading="loading"
          :disabled="isIgnoringDisabled"
          :model-value="isIgnored"
          data-testid="managed-asset-ignore-switch"
          @update:model-value="emit('toggle-ignore')"
        />
      </template>
      {{ tooltipMessage }}
    </RuiTooltip>

    <RuiMenu
      v-if="showMoreOptions"
      :class-names="{ menu: 'w-60' }"
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
            variant="text"
            v-bind="attrs"
            size="sm"
            :loading="menuLoading"
            class="text-rui-text-secondary!"
            :aria-label="t('common.actions.more')"
          >
            <RuiIcon
              name="lu-ellipsis-vertical"
              size="18"
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
              details="hidden"
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
              details="hidden"
              :model-value="isSpam"
            />
          </template>
          {{ t('ignore.spam.action.add') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
