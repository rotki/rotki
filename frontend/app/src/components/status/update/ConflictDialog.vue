<template>
  <v-bottom-sheet persistent v-bind="$attrs" width="98%" v-on="$listeners">
    <card outlined-body>
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
        class="conflict-dialog__table"
        :items="conflicts"
        :headers="headers"
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
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import ConflictRow from '@/components/status/update/ConflictRow.vue';
import {
  ConflictResolution,
  ConflictResolutionStrategy,
  SupportedAsset
} from '@/services/assets/types';
import { AssetUpdateConflictResult } from '@/store/assets/types';
import { Writeable } from '@/types';
import { uniqueStrings } from '@/utils/data';

@Component({
  components: { ConflictRow }
})
export default class ConflictDialog extends Vue {
  @Prop({ required: true, type: Array })
  conflicts!: AssetUpdateConflictResult[];
  resolution: ConflictResolution = {};

  @Emit()
  resolve(_resolution: ConflictResolution) {}
  @Emit()
  cancel() {}

  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('conflict_dialog.table.headers.local').toString(),
      sortable: false,
      value: 'local'
    },
    {
      text: this.$t('conflict_dialog.table.headers.remote').toString(),
      sortable: false,
      value: 'remote'
    },
    {
      text: this.$t('conflict_dialog.table.headers.keep').toString(),
      value: 'keep',
      align: 'center',
      sortable: false,
      class: 'conflict-dialog__action-container'
    }
  ];

  setResolution(strategy: ConflictResolutionStrategy) {
    const length = this.conflicts.length;
    const resolution: Writeable<ConflictResolution> = {};
    for (let i = 0; i < length; i++) {
      const conflict = this.conflicts[i];
      resolution[conflict.identifier] = strategy;
    }

    this.resolution = resolution;
  }

  getConflictFields(conflict: AssetUpdateConflictResult): string[] {
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
  }

  isDiff(conflict: AssetUpdateConflictResult, field: keyof SupportedAsset) {
    const localElement = conflict.local[field];
    const remoteElement = conflict.remote[field];
    return localElement !== remoteElement;
  }

  get valid(): boolean {
    const identifiers = this.conflicts
      .map(({ identifier }) => identifier)
      .sort();
    const resolved = Object.keys(this.resolution).sort();
    if (identifiers.length !== resolved.length) {
      return false;
    }

    for (let i = 0; i < resolved.length; i++) {
      if (resolved[i] !== identifiers[i]) {
        return false;
      }
    }
    return true;
  }

  get remaining(): number {
    const resolved = Object.keys(this.resolution).length;
    return this.conflicts.length - resolved;
  }
}
</script>

<style scoped lang="scss">
@import '~@/scss/scroll';

::v-deep {
  .v-card {
    border-bottom-left-radius: 0 !important;
    border-bottom-right-radius: 0 !important;
  }
}

.conflict-dialog {
  &__table {
    height: calc(100vh - 550px);
    overflow-y: auto;

    ::v-deep {
      .v-data-footer {
        position: fixed;
        bottom: 48px;
        left: 0;
        right: 0;
        margin-left: 40px;
        margin-right: 40px;
        border-top: none !important;
        @media (max-width: 450px) {
          margin-left: 8px;
          margin-right: 8px;
        }
        @media (max-width: 700px) {
          margin-left: 16px;
          margin-right: 16px;
        }
      }
    }

    @media (max-width: 450px) {
      height: calc(100vh - 690px);
    }

    @media (max-height: 700px) {
      height: calc(100vh - 360px);
    }

    @media (min-height: 701px) and (max-height: 1024px) {
      height: calc(100vh - 388px);
    }

    @extend .themed-scrollbar;
  }

  &__action {
    width: 90px;
  }

  &__pagination {
    height: 70px;
    @media (max-width: 450px) {
      height: 120px;
    }
  }

  &__action-container {
    width: 200px;
  }
}
</style>
