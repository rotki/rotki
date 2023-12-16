<script setup lang="ts">
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

const { t } = useI18n();

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
        <RuiButton
          class="!p-1"
          icon
          variant="text"
          v-bind="attrs"
        >
          <RuiIcon
            name="arrow-down-s-line"
            size="20"
          />
        </RuiButton>
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
              :value="isWhitelisted"
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
              :value="isSpam"
            />
          </template>
          {{ t('ignore.spam.action.add') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
