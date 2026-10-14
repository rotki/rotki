<script setup lang="ts">
import { type Nullable, transformCase } from '@rotki/common';
import QueriedAddressDialog from '@/modules/accounts/QueriedAddressDialog.vue';
import { useQueriedAddressOperations } from '@/modules/accounts/use-queried-address-operations';
import { type Module, SUPPORTED_MODULES } from '@/modules/core/common/modules';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';
import AppImage from '@/modules/shell/components/AppImage.vue';

interface ModuleRow {
  readonly identifier: Module;
  readonly name: string;
  readonly icon: string;
  readonly enabled: boolean;
}

/**
 * A page's settings behind one header button: the modules the page depends on, and whatever the
 * page adds below them (an optional API key, say). The modules used to be a row of bare logo
 * buttons whose meaning only showed on hover.
 */
const { attentionHint, modules } = defineProps<{
  modules: Module[];
  /**
   * Why something inside wants a look, such as an unanswered key offer. While set, the button
   * carries a dot and its tooltip says this under the title, so the dot is not a riddle.
   */
  attentionHint?: string;
}>();

defineSlots<{
  default?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const open = ref<boolean>(false);
const manageModule = ref<Nullable<Module>>(null);

const activeModules = useSetting('activeModules');
const { update } = useSettingsOperations();
const { fetchQueriedAddresses } = useQueriedAddressOperations();
const { queriedAddresses } = storeToRefs(useSessionMetadataStore());
const { show } = useConfirmStore();

const rows = computed<ModuleRow[]>(() => {
  const active = get(activeModules);
  return modules.map((identifier) => {
    const data = SUPPORTED_MODULES.find(value => value.identifier === identifier);
    return {
      enabled: active.includes(identifier),
      icon: data?.icon ?? '',
      identifier,
      name: data?.name ?? identifier,
    };
  });
});

/** With none listed every address is queried; listing some limits the module to those. */
function addressCount(module: Module): number {
  return (get(queriedAddresses)[transformCase(module, true)] ?? []).length;
}

function manageAddresses(module: Module): void {
  set(open, false);
  set(manageModule, module);
}

function enable(row: ModuleRow): void {
  set(open, false);
  show(
    {
      message: t('active_modules.enable.description', { name: row.name }),
      title: t('active_modules.enable.title'),
      type: 'info',
    },
    async () => update({ activeModules: [...get(activeModules), row.identifier] }),
  );
}

onMounted(async () => {
  await fetchQueriedAddresses();
});
</script>

<template>
  <RuiMenu
    v-model="open"
    :options="{ placement: 'bottom-end' }"
    :menu-label="t('page_settings.title')"
  >
    <template #activator="{ attrs }">
      <RuiTooltip
        :options="{ placement: 'bottom' }"
        :open-delay="250"
        :close-delay="0"
      >
        <template #activator>
          <RuiButton
            v-bind="attrs"
            variant="text"
            icon
            class="relative text-rui-text-secondary!"
            data-testid="module-settings"
            :aria-label="t('page_settings.title')"
            :aria-description="attentionHint"
          >
            <RuiIcon name="lu-sliders-horizontal" />
            <span
              v-if="attentionHint"
              class="absolute top-1.5 right-1.5 size-2 rounded-full bg-rui-info ring-2 ring-rui-surface"
              data-testid="module-settings-attention"
            />
          </RuiButton>
        </template>
        <div class="flex flex-col max-w-64">
          <span>{{ t('page_settings.title') }}</span>
          <span
            v-if="attentionHint"
            class="text-xs opacity-80"
          >
            {{ attentionHint }}
          </span>
        </div>
      </RuiTooltip>
    </template>

    <div class="w-[26rem] max-w-full p-4 flex flex-col gap-4">
      <section
        v-for="row in rows"
        :key="row.identifier"
        class="flex items-start justify-between gap-4"
        data-testid="module-settings-module"
        :data-module="row.identifier"
      >
        <div class="flex items-start gap-3 min-w-0">
          <AppImage
            :src="row.icon"
            size="1.5rem"
            fit="contain"
            class="shrink-0 mt-0.5"
            :class="{ grayscale: !row.enabled }"
          />
          <div class="min-w-0">
            <h3 class="text-subtitle-2 font-medium m-0">
              {{ t('page_settings.module', { name: row.name }) }}
            </h3>
            <p class="text-body-2 text-rui-text-secondary m-0 mt-0.5">
              <template v-if="!row.enabled">
                {{ t('page_settings.disabled') }}
              </template>
              <template v-else-if="addressCount(row.identifier) === 0">
                {{ t('page_settings.all_addresses') }}
              </template>
              <template v-else>
                {{ t('page_settings.some_addresses', { count: addressCount(row.identifier) }, addressCount(row.identifier)) }}
              </template>
            </p>
          </div>
        </div>
        <RuiButton
          v-if="row.enabled"
          size="sm"
          variant="outlined"
          color="primary"
          class="shrink-0"
          data-testid="module-settings-addresses"
          @click="manageAddresses(row.identifier)"
        >
          {{ t('page_settings.manage_addresses') }}
        </RuiButton>
        <RuiButton
          v-else
          size="sm"
          color="primary"
          class="shrink-0"
          data-testid="module-settings-enable"
          @click="enable(row)"
        >
          {{ t('page_settings.enable') }}
        </RuiButton>
      </section>

      <template v-if="$slots.default">
        <RuiDivider />
        <slot />
      </template>
    </div>
  </RuiMenu>

  <QueriedAddressDialog
    v-if="manageModule"
    :module="manageModule"
    @close="manageModule = null"
  />
</template>
