<template>
  <v-bottom-sheet v-bind="$attrs" persistent width="98%" v-on="$listeners">
    <card outlined-body contained no-radius-bottom>
      <template #title>{{ $t('conflict_dialog.title') }}</template>
      <template #subtitle>{{ $t('conflict_dialog.subtitle') }}</template>
      <template #actions>
        <v-row no-gutters justify="end" align="center">
          <v-col cols="auto">
            <span class="pe-2">
              {{ $t('conflict_dialog.all_buttons_description') }}
            </span>
          </v-col>
          <v-col cols="auto">
            <v-row no-gutters justify="end">
              <v-btn text value="local" @click="setResolution('local')">
                {{ $t('conflict_dialog.keep_local') }}
              </v-btn>
              <v-btn text value="remote" @click="setResolution('remote')">
                {{ $t('conflict_dialog.keep_remote') }}
              </v-btn>
            </v-row>
          </v-col>
        </v-row>
      </template>
      <template #hint>
        <i18n path="conflict_dialog.hint" tag="span">
          <template #conflicts>
            <span class="font-weight-medium"> {{ conflicts.length }} </span>
          </template>
          <template #remaining>
            <span class="font-weight-medium"> {{ remaining }} </span>
          </template>
        </i18n>
      </template>
      <data-table
        :class="{
          [$style.mobile]: true
        }"
        :items="conflicts"
        :headers="tableHeaders"
      >
        <template #item.local="{ item: conflict }">
          <conflict-row
            v-for="field in getConflictFields(conflict)"
            :key="`local-${field}`"
            :field="field"
            :value="conflict.local[field]"
            :diff="isDiff(conflict, field)"
          />
        </template>
        <template #item.remote="{ item: conflict }">
          <conflict-row
            v-for="field in getConflictFields(conflict)"
            :key="`remote-${field}`"
            :field="field"
            :value="conflict.remote[field]"
            :diff="isDiff(conflict, field)"
          />
        </template>
        <template #item.keep="{ item: conflict }">
          <v-btn-toggle v-model="resolution[conflict.identifier]">
            <v-btn class="conflict-dialog__action" value="local">
              {{ $t('conflict_dialog.action.local') }}
            </v-btn>
            <v-btn class="conflict-dialog__action" value="remote">
              {{ $t('conflict_dialog.action.remote') }}
            </v-btn>
          </v-btn-toggle>
        </template>
      </data-table>
      <template #options>
        <div class="conflict-dialog__pagination" />
      </template>
      <template #buttons>
        <v-row no-gutters justify="end">
          <v-col cols="auto">
            <v-btn text @click="cancel">
              {{ $t('conflict_dialog.buttons.cancel') }}
            </v-btn>
          </v-col>
          <v-col cols="auto">
            <v-btn
              text
              color="primary"
              :disabled="!valid"
              @click="resolve(resolution)"
            >
              {{ $t('conflict_dialog.buttons.confirm') }}
            </v-btn>
          </v-col>
        </v-row>
      </template>
    </card>
  </v-bottom-sheet>
</template>

<script lang="ts">
import { SupportedAsset } from '@rotki/common/lib/data';
import {
  computed,
  defineComponent,
  PropType,
  Ref,
  ref,
  toRefs
} from '@vue/composition-api';
import { IVueI18n } from 'vue-i18n';
import { DataTableHeader } from 'vuetify';
import ConflictRow from '@/components/status/update/ConflictRow.vue';
import { setupThemeCheck } from '@/composables/common';
import i18n from '@/i18n';
import {
  ConflictResolution,
  ConflictResolutionStrategy
} from '@/services/assets/types';
import { AssetUpdateConflictResult } from '@/store/assets/types';
import { Writeable } from '@/types';
import { uniqueStrings } from '@/utils/data';

const getHeaders: (
  i18n: IVueI18n,
  isMobile: Ref<boolean>
) => DataTableHeader[] = i18n => {
  return [
    {
      text: i18n.t('conflict_dialog.table.headers.local').toString(),
      sortable: false,
      value: 'local'
    },
    {
      text: i18n.t('conflict_dialog.table.headers.remote').toString(),
      sortable: false,
      value: 'remote'
    },
    {
      text: i18n.t('conflict_dialog.table.headers.keep').toString(),
      value: 'keep',
      align: 'center',
      sortable: false,
      class: 'conflict-dialog__action-container'
    }
  ];
};

const ConflictDialog = defineComponent({
  name: 'ConflictDialog',
  components: { ConflictRow },
  props: {
    conflicts: {
      required: true,
      type: Array as PropType<AssetUpdateConflictResult[]>
    }
  },
  emits: ['resolve', 'cancel'],
  setup(props, { emit }) {
    const { conflicts } = toRefs(props);
    const resolution: Ref<ConflictResolution> = ref({});
    const setResolution = (strategy: ConflictResolutionStrategy) => {
      const length = conflicts.value.length;
      const resolutionStrategy: Writeable<ConflictResolution> = {};
      for (let i = 0; i < length; i++) {
        const conflict = conflicts.value[i];
        resolutionStrategy[conflict.identifier] = strategy;
      }

      resolution.value = resolutionStrategy;
    };

    const getConflictFields = (
      conflict: AssetUpdateConflictResult
    ): string[] => {
      function nonNull(
        key: keyof SupportedAsset,
        asset: SupportedAsset
      ): boolean {
        return asset[key] !== null;
      }
      const remote = Object.keys(conflict.remote).filter(value =>
        nonNull(value as keyof SupportedAsset, conflict.remote)
      );
      const local = Object.keys(conflict.local).filter(value =>
        nonNull(value as keyof SupportedAsset, conflict.local)
      );
      return [...remote, ...local].filter(uniqueStrings);
    };

    const isDiff = (
      conflict: AssetUpdateConflictResult,
      field: keyof SupportedAsset
    ) => {
      const localElement = conflict.local[field];
      const remoteElement = conflict.remote[field];
      return localElement !== remoteElement;
    };

    const remaining = computed(() => {
      const resolved = Object.keys(resolution.value).length;
      return conflicts.value.length - resolved;
    });

    const valid = computed(() => {
      const identifiers = conflicts.value
        .map(({ identifier }) => identifier)
        .sort();
      const resolved = Object.keys(resolution.value).sort();
      if (identifiers.length !== resolved.length) {
        return false;
      }

      for (let i = 0; i < resolved.length; i++) {
        if (resolved[i] !== identifiers[i]) {
          return false;
        }
      }
      return true;
    });

    const resolve = (resolution: ConflictResolution) => {
      emit('resolve', resolution);
    };

    const cancel = () => {
      emit('cancel');
    };

    const { isMobile } = setupThemeCheck();

    return {
      isDiff,
      setResolution,
      getConflictFields,
      tableHeaders: getHeaders(i18n, isMobile),
      resolution,
      remaining,
      valid,
      cancel,
      resolve,
      isMobile
    };
  }
});

export default ConflictDialog;
</script>

<style module lang="scss">
.mobile {
  :global {
    .v-data-table {
      &__mobile-row {
        padding: 12px 16px !important;

        &__header {
          text-orientation: sideways;
          writing-mode: vertical-lr;
        }
      }

      &__mobile-table-row {
        td {
          &:nth-child(2) {
            background-color: rgba(0, 0, 0, 0.1);
          }
        }
      }
    }
  }
}
</style>
