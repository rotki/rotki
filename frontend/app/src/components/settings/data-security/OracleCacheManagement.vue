<template>
  <fragment>
    <v-card class="mt-8">
      <v-card-title>
        <card-title>{{ $t('oracle_cache_management.title') }}</card-title>
      </v-card-title>
      <v-card-subtitle>
        {{ $t('oracle_cache_management.subtitle') }}
      </v-card-subtitle>
      <v-card-text>
        <v-row no-gutters align="center">
          <v-col>
            <v-autocomplete
              v-model="selection"
              :label="$t('oracle_cache_management.select_oracle')"
              prepend-inner-icon="mdi-magnify"
              outlined
              :items="oracles"
            >
              <template #selection="{ item }">
                <oracle-entry :identifier="item" />
              </template>
              <template #item="{ item }">
                <oracle-entry :identifier="item" />
              </template>
            </v-autocomplete>
          </v-col>
          <v-col cols="auto" />
        </v-row>
        <v-row align="center">
          <v-col>
            <asset-select
              v-model="fromAsset"
              :disabled="pending"
              outlined
              :label="$t('oracle_cache_management.from_asset')"
            />
          </v-col>
          <v-col>
            <asset-select
              v-model="toAsset"
              :disabled="pending"
              outlined
              :label="$t('oracle_cache_management.to_asset')"
            />
          </v-col>
          <v-col cols="auto">
            <v-tooltip open-delay="400" top>
              <template #activator="{ on, attrs }">
                <div class="pb-7">
                  <v-btn
                    v-bind="attrs"
                    text
                    :loading="pending"
                    color="primary"
                    :disabled="!fromAsset || !toAsset || pending"
                    v-on="on"
                    @click="fetchPrices()"
                  >
                    {{ $t('oracle_cache_management.create_cache') }}
                  </v-btn>
                </div>
              </template>
              <span>{{ $t('oracle_cache_management.create_tooltip') }}</span>
            </v-tooltip>
          </v-col>
        </v-row>
        <v-divider class="mb-4" />
        <v-row justify="end">
          <v-col cols="auto">
            <v-text-field
              v-model="search"
              outlined
              dense
              prepend-inner-icon="mdi-magnify"
              :label="$t('oracle_cache_management.filter')"
            />
          </v-col>
        </v-row>
        <v-sheet outlined rounded>
          <data-table
            :search.sync="search"
            :headers="headers"
            :loading="loading"
            :items="cacheData"
          >
            <template #item.fromAsset="{ item }">
              <asset-details opens-details :asset="item.fromAsset" />
            </template>
            <template #item.toAsset="{ item }">
              <asset-details opens-details :asset="item.toAsset" />
            </template>
            <template #item.toTimestamp="{ item }">
              <date-display :timestamp="item.toTimestamp" />
            </template>
            <template #item.fromTimestamp="{ item }">
              <date-display :timestamp="item.fromTimestamp" />
            </template>
            <template #item.actions="{ item }">
              <v-tooltip open-delay="400" top>
                <template #activator="{ on, attrs }">
                  <v-btn
                    color="primary"
                    v-bind="attrs"
                    icon
                    v-on="on"
                    @click="confirmDelete(item)"
                  >
                    <v-icon>mdi-delete</v-icon>
                  </v-btn>
                </template>
                <span>{{ $t('oracle_cache_management.delete_tooltip') }}</span>
              </v-tooltip>
            </template>
          </data-table>
        </v-sheet>
      </v-card-text>
    </v-card>
    <confirm-dialog
      :display="confirmClear"
      :title="$t('oracle_cache_management.delete_confirmation.title')"
      :message="
        $t('oracle_cache_management.delete_confirmation.message', {
          selection,
          fromAsset: deleteFromAsset,
          toAsset: deleteToAsset
        })
      "
      @confirm="clearCache"
      @cancel="confirmClear = false"
    />
  </fragment>
</template>

<script lang="ts">
import { Ref } from '@vue/composition-api';
import { mapState } from 'pinia';
import { Component, Vue, Watch } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { mapActions } from 'vuex';
import ConfirmDialog from '@/components/dialogs/ConfirmDialog.vue';
import ActionStatusIndicator from '@/components/error/ActionStatusIndicator.vue';
import DataTable from '@/components/helper/DataTable.vue';
import Fragment from '@/components/helper/Fragment';
import OracleEntry from '@/components/settings/OracleEntry.vue';
import { OracleCacheMeta } from '@/services/balances/types';
import { OracleCachePayload } from '@/store/balances/types';
import { useNotifications } from '@/store/notifications';
import { Severity } from '@/store/notifications/consts';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { TaskType } from '@/types/task-type';
import { PriceOracle } from '@/types/user';
import { assert } from '@/utils/assertions';

@Component({
  components: {
    DataTable,
    ActionStatusIndicator,
    ConfirmDialog,
    Fragment,
    OracleEntry
  },
  computed: {
    ...mapState(useTasks, ['isTaskRunning'])
  },
  methods: {
    ...mapActions('balances', ['createOracleCache'])
  }
})
export default class OracleCacheManagement extends Vue {
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('oracle_cache_management.headers.from').toString(),
      value: 'fromAsset'
    },
    {
      text: this.$t('oracle_cache_management.headers.to').toString(),
      value: 'toAsset'
    },
    {
      text: this.$t('oracle_cache_management.headers.from_date').toString(),
      value: 'fromTimestamp'
    },
    {
      text: this.$t('oracle_cache_management.headers.to_date').toString(),
      value: 'toTimestamp'
    },
    {
      text: '',
      value: 'actions'
    }
  ];
  readonly oracles: PriceOracle[] = ['cryptocompare'];

  loading: boolean = false;
  confirmClear: boolean = false;
  cacheData: OracleCacheMeta[] = [];
  fromAsset: string = '';
  toAsset: string = '';
  search: string = '';
  selection: PriceOracle = 'cryptocompare';
  deleteEntry: OracleCacheMeta | null = null;
  createOracleCache!: (payload: OracleCachePayload) => Promise<ActionStatus>;
  isTaskRunning!: (type: TaskType) => Ref<boolean>;

  @Watch('selection')
  async onSelectionChanged() {
    await this.load();
  }

  get deleteFromAsset(): string {
    if (this.deleteEntry) {
      return this.deleteEntry.fromAsset;
    }
    return '';
  }

  get deleteToAsset(): string {
    if (this.deleteEntry) {
      return this.deleteEntry.toAsset;
    }
    return '';
  }

  get pending(): boolean {
    return this.isTaskRunning(TaskType.CREATE_PRICE_CACHE).value;
  }

  async mounted() {
    await this.load();
  }

  private async load() {
    this.loading = true;
    this.cacheData = await this.$api.balances.getPriceCache('cryptocompare');
    this.loading = false;
  }

  confirmDelete(entry: OracleCacheMeta) {
    this.confirmClear = true;
    this.deleteEntry = entry;
  }

  async clearCache() {
    assert(this.deleteEntry);
    const { fromAsset, toAsset } = this.deleteEntry;
    this.confirmClear = false;
    this.deleteEntry = null;
    try {
      await this.$api.balances.deletePriceCache(
        this.selection,
        fromAsset,
        toAsset
      );
      await this.load();
    } catch (e: any) {
      const title = this.$t(
        'oracle_cache_management.notification.title'
      ).toString();

      const message = this.$t('oracle_cache_management.clear_error', {
        fromAsset,
        toAsset,
        error: e.message
      }).toString();

      const { notify } = useNotifications();
      notify({
        title,
        message,
        severity: Severity.ERROR,
        display: true
      });
    }
  }

  async fetchPrices() {
    const fromAsset = this.fromAsset;
    const toAsset = this.toAsset;
    const source = this.selection;
    this.fromAsset = '';
    this.toAsset = '';

    const status = await this.createOracleCache({
      purgeOld: false,
      fromAsset: fromAsset,
      toAsset: toAsset,
      source: source
    });

    if (status.success) {
      await this.load();
    }

    const message = status.success
      ? this.$t('oracle_cache_management.notification.success', {
          fromAsset,
          toAsset,
          source
        })
      : this.$t('oracle_cache_management.notification.error', {
          fromAsset,
          toAsset,
          source,
          error: status.message
        });
    const title = this.$t(
      'oracle_cache_management.notification.title'
    ).toString();

    const { notify } = useNotifications();
    notify({
      title,
      message: message.toString(),
      severity: status.success ? Severity.INFO : Severity.ERROR,
      display: true
    });
  }
}
</script>
