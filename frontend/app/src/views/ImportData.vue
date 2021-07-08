<template>
  <v-container>
    <base-page-header :text="$t('import_data.title')" />
    <v-card outlined>
      <v-card-text>
        <v-row>
          <v-col cols="12">
            <v-row>
              <v-col cols="12" v-text="$t('import_data.description')" />
              <v-col cols="12">
                <i18n tag="span" path="import_data.notice">
                  <template #warning>
                    <strong v-text="$t('import_data.notice_warning')" />
                  </template>
                  <template #link>
                    <external-link
                      url="https://github.com/rotki/rotki/issues/new/choose"
                      v-text="$t('import_data.notice_link')"
                    />
                  </template>
                </i18n>
              </v-col>
            </v-row>
            <v-divider class="mt-2 mb-4" />
            <v-row>
              <v-col cols="12">
                <v-img
                  max-width="200"
                  class="import-data__cointracking-info"
                  :src="require('@/assets/images/import/cointracking_info.png')"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <file-upload source="cointracking.info" />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <i18n tag="span" path="import_data.cointracking.note">
                  <strong v-text="$t('import_data.cointracking.name')" />
                </i18n>
                <ul>
                  <li>{{ $t('import_data.cointracking.line_one') }}</li>
                  <li>{{ $t('import_data.cointracking.line_two') }}</li>
                  <i18n path="import_data.cointracking.line_three">
                    <router-link
                      to="/accounts-balance"
                      v-text="$t('import_data.cointracking.link')"
                    />
                  </i18n>
                </ul>
              </v-col>
            </v-row>
            <v-row>
              <v-col
                cols="12"
                v-text="$t('import_data.cointracking.preferred')"
              />
            </v-row>
            <v-divider class="mt-2 mb-4" />
            <v-row>
              <v-col cols="12">
                <div class="import-data__crypto-com">
                  <v-img
                    max-width="200"
                    :src="require('@/assets/images/import/crypto_com.png')"
                  />
                </div>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <file-upload source="cryptocom" />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12">
                <i18n tag="span" path="import_data.cryptocom.note">
                  <strong v-text="$t('import_data.cryptocom.name')" />
                </i18n>

                <ul>
                  <li>
                    <i18n tag="span" path="import_data.cryptocom.line_one">
                      <external-link
                        url="https://github.com/rotki/rotki/issues/new/choose"
                        v-text="$t('import_data.cryptocom.line_one_link')"
                      />
                    </i18n>
                  </li>
                  <li>
                    <i18n tag="span" path="import_data.cryptocom.line_two">
                      <strong
                        v-text="$t('import_data.cryptocom.line_two_warning')"
                      />
                    </i18n>
                  </li>
                  <li v-text="$t('import_data.cryptocom.line_three')" />
                  <li>
                    <i18n path="import_data.cryptocom.line_four" tag="span">
                      <router-link
                        to="/accounts-balance/manual-balances"
                        v-text="$t('import_data.cryptocom.line_four_link')"
                      />
                    </i18n>
                  </li>
                </ul>
              </v-col>
            </v-row>
            <v-divider class="mt-2 mb-4" />
            <v-row>
              <v-col cols="12">
                <div class="import-data__crypto-com">
                  <v-img
                    max-width="200"
                    :src="require('@/assets/images/import/blockfi.svg')"
                  />
                </div>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <i18n tag="span" path="import_data.blockfi.import">
                  <strong v-text="$t('import_data.blockfi.import_trade')" />
                </i18n>
                <file-upload source="blockfi-trades" class="mt-2" />
              </v-col>
              <v-col>
                <i18n tag="span" path="import_data.blockfi.import">
                  <strong
                    v-text="$t('import_data.blockfi.import_transactions')"
                  />
                </i18n>
                <file-upload source="blockfi-transactions" class="mt-2" />
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <i18n tag="span" path="import_data.blockfi.note">
                  <strong v-text="$t('import_data.blockfi.name')" />
                </i18n>
                <ul>
                  <li>{{ $t('import_data.blockfi.line_one') }}</li>
                  <li>{{ $t('import_data.blockfi.line_two') }}</li>
                </ul>
              </v-col>
            </v-row>
            <v-divider class="mt-2 mb-4" />
            <v-row>
              <v-col cols="12">
                <div class="import-data__crypto-com">
                  <v-img
                    max-width="200"
                    :src="require('@/assets/images/import/nexo.svg')"
                  />
                </div>
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <i18n tag="span" path="import_data.nexo.import">
                  <strong v-text="$t('import_data.nexo.import_transactions')" />
                </i18n>
                <file-upload source="nexo" class="mt-2" />
              </v-col>
            </v-row>
            <v-row>
              <v-col>
                <i18n tag="span" path="import_data.nexo.note">
                  <strong v-text="$t('import_data.nexo.name')" />
                </i18n>
                <ul>
                  <li>{{ $t('import_data.nexo.line_one') }}</li>
                </ul>
              </v-col>
            </v-row>
            <v-divider class="mt-2 mb-4" />
            <div v-if="premium">
              <v-row>
                <v-col cols="12">
                  <v-img
                    max-width="200"
                    class="import-data__gitcoin"
                    :src="require('@/assets/images/import/gitcoin.svg')"
                  />
                </v-col>
              </v-row>
              <v-row>
                <v-col>
                  <file-upload source="gitcoin" />
                </v-col>
              </v-row>
              <v-row>
                <v-col cols="12">
                  <span>{{ $t('import_data.gitcoin.description') }}</span>
                </v-col>
              </v-row>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-container>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import BasePageHeader from '@/components/base/BasePageHeader.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import FileUpload from '@/components/import/FileUpload.vue';
import PremiumMixin from '@/mixins/premium-mixin';

@Component({
  components: { FileUpload, BasePageHeader, ExternalLink }
})
export default class ImportData extends Mixins(PremiumMixin) {}
</script>

<style scoped lang="scss">
.import-data {
  &__crypto-com {
    max-width: 200px;
    padding: 10px;
  }
}
</style>
