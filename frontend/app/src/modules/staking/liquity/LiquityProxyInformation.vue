<script setup lang="ts">
import HashLink from '@/modules/shell/components/HashLink.vue';

const { proxyInformation } = defineProps<{
  proxyInformation: Record<string, string[]>;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiMenu
    :options="{ placement: 'right-start' }"
    menu-class="max-w-[25rem]"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        class="!p-2"
        icon
        v-bind="attrs"
      >
        <RuiIcon name="lu-info" />
      </RuiButton>
    </template>
    <div class="p-3 px-4">
      <div
        v-for="(proxies, key, index) in proxyInformation"
        :key="key"
      >
        <div class="flex items-center gap-2">
          <HashLink
            :text="key"
            class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 rounded-full m-0.5"
          />
          <span class="text-sm">
            {{
              t('liquity_staking_details.has_proxy_addresses', {
                length: proxies.length,
              })
            }}
          </span>
        </div>
        <div class="ml-3 pl-4 pt-2 relative before:content-[''] before:absolute before:top-0 before:left-0 before:border-l before:border-rui-grey-200 before:h-[calc(100%-0.8rem)] dark:before:border-rui-grey-800">
          <div
            v-for="proxy in proxies"
            :key="proxy"
            class="mb-1 flex relative before:content-[''] before:absolute before:w-4 before:right-full before:top-1/2 before:border-t before:border-rui-grey-200 dark:before:border-rui-grey-800"
          >
            <HashLink
              :text="proxy"
              class="bg-rui-grey-300 dark:bg-rui-grey-800 pr-1 rounded-full m-0.5"
            />
          </div>
        </div>
        <RuiDivider
          v-if="index < Object.keys(proxyInformation).length - 1"
          class="my-4"
        />
      </div>
    </div>
  </RuiMenu>
</template>
