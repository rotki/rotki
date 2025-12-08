import type { ActionResult } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiValidationError } from '@/types/api/errors';
import { useSettingsApi } from './settings-api';

const backendUrl = process.env.VITE_BACKEND_URL;

interface CapturedRequest {
  body: unknown;
  headers: Headers;
  url: string;
  method: string;
}

function createSettingsResponse(overrides: Record<string, unknown> = {}): ActionResult<Record<string, unknown>> {
  return {
    result: {
      have_premium: false,
      version: 42,
      last_write_ts: 1712774152,
      premium_should_sync: false,
      include_crypto2crypto: true,
      ui_floating_precision: 2,
      taxfree_after_period: 31536000,
      balance_save_frequency: 24,
      include_gas_costs: true,
      ksm_rpc_endpoint: 'http://localhost:9933',
      dot_rpc_endpoint: '',
      beacon_rpc_endpoint: '',
      btc_mempool_api: '',
      main_currency: 'EUR',
      date_display_format: '%d/%m/%Y %H:%M:%S %Z',
      submit_usage_analytics: true,
      active_modules: [],
      frontend_settings: '{}',
      btc_derivation_gap_limit: 20,
      calculate_past_cost_basis: true,
      display_date_in_localtime: true,
      current_price_oracles: ['coingecko'],
      historical_price_oracles: ['cryptocompare'],
      pnl_csv_with_formulas: true,
      pnl_csv_have_summary: false,
      ssf_graph_multiplier: 0,
      last_data_migration: 13,
      non_syncing_exchanges: [],
      evmchains_to_skip_detection: [],
      cost_basis_method: 'fifo',
      treat_eth2_as_eth: true,
      eth_staking_taxable_after_withdrawal_enabled: true,
      address_name_priority: ['private_addressbook'],
      include_fees_in_cost_basis: true,
      infer_zero_timed_balances: false,
      query_retry_limit: 5,
      connect_timeout: 30,
      read_timeout: 30,
      oracle_penalty_threshold_count: 5,
      oracle_penalty_duration: 1800,
      last_balance_save: 0,
      last_data_upload_ts: 0,
      auto_delete_calendar_entries: true,
      auto_create_calendar_reminders: true,
      ask_user_upon_size_discrepancy: true,
      auto_detect_tokens: true,
      csv_export_delimiter: ',',
      default_evm_indexer_order: [],
      evm_indexers_order: {},
      ...overrides,
    },
    message: '',
  };
}

function createBackendConfigResponse(): ActionResult<Record<string, unknown>> {
  return {
    result: {
      loglevel: { is_default: true, value: 'DEBUG' },
      max_logfiles_num: { is_default: true, value: 3 },
      max_size_in_mb_all_logs: { is_default: true, value: 300 },
      sqlite_instructions: { is_default: true, value: 5000 },
    },
    message: '',
  };
}

describe('composables/api/settings/settings-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('getSettings', () => {
    it('sends GET request and transforms response from snake_case to camelCase', async () => {
      let capturedRequest: CapturedRequest | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/settings`, ({ request }) => {
          capturedRequest = {
            body: null,
            headers: request.headers,
            url: request.url,
            method: request.method,
          };
          return HttpResponse.json(createSettingsResponse({ main_currency: 'USD' }));
        }),
      );

      const { getSettings } = useSettingsApi();
      const result = await getSettings();

      expect(capturedRequest).not.toBeNull();
      expect(capturedRequest!.method).toBe('GET');
      expect(capturedRequest!.url).toBe(`${backendUrl}/api/1/settings`);

      // Verify response was transformed to camelCase and parsed
      expect(result.general.mainCurrency).toBeDefined();
      expect(result.other.havePremium).toBe(false);
      expect(result.accounting.includeCrypto2crypto).toBe(true);
    });

    it('throws error when result is null', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/settings`, () =>
          HttpResponse.json({
            result: null,
            message: 'No settings found',
          }, { status: 200 })),
      );

      const { getSettings } = useSettingsApi();

      await expect(getSettings()).rejects.toThrow('No settings found');
    });
  });

  describe('setSettings', () => {
    it('sends PUT request with snake_case payload', async () => {
      let capturedRequest: CapturedRequest | null = null;
      let capturedBody: unknown = null;

      server.use(
        http.put(`${backendUrl}/api/1/settings`, async ({ request }) => {
          capturedBody = await request.json();
          capturedRequest = {
            body: capturedBody,
            headers: request.headers,
            url: request.url,
            method: request.method,
          };
          return HttpResponse.json(createSettingsResponse({ main_currency: 'GBP' }));
        }),
      );

      const { setSettings } = useSettingsApi();
      await setSettings({ mainCurrency: 'GBP', uiFloatingPrecision: 4 });

      expect(capturedRequest).not.toBeNull();
      expect(capturedRequest!.method).toBe('PUT');

      // Verify request payload was transformed to snake_case
      expect(capturedBody).toEqual({
        settings: {
          main_currency: 'GBP',
          ui_floating_precision: 4,
        },
      });
    });

    it('transforms response from snake_case to camelCase', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/settings`, () =>
          HttpResponse.json(createSettingsResponse({
            main_currency: 'GBP',
            ui_floating_precision: 4,
          }))),
      );

      const { setSettings } = useSettingsApi();
      const result = await setSettings({ mainCurrency: 'GBP' });

      // Verify response was transformed and parsed correctly
      expect(result.general.uiFloatingPrecision).toBe(4);
    });

    it('throws ApiValidationError on 400 response', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/settings`, () =>
          HttpResponse.json({
            result: null,
            message: '{"main_currency": ["Invalid currency code"]}',
          }, { status: 400 })),
      );

      const { setSettings } = useSettingsApi();

      await expect(setSettings({ mainCurrency: 'INVALID' }))
        .rejects
        .toThrow(ApiValidationError);
    });

    it('throws ApiValidationError with parsed validation errors', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/settings`, () =>
          HttpResponse.json({
            result: null,
            message: '{"ui_floating_precision": ["Must be between 0 and 8"]}',
          }, { status: 400 })),
      );

      const { setSettings } = useSettingsApi();

      try {
        await setSettings({ uiFloatingPrecision: 100 });
        expect.fail('Should have thrown ApiValidationError');
      }
      catch (error) {
        expect(error).toBeInstanceOf(ApiValidationError);
        const validationError = error as ApiValidationError;
        // Errors should be transformed to camelCase
        expect(validationError.errors).toHaveProperty('uiFloatingPrecision');
      }
    });

    it('throws generic Error on non-400 error response', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/settings`, () =>
          HttpResponse.json({
            result: null,
            message: 'Internal server error',
          }, { status: 500 })),
      );

      const { setSettings } = useSettingsApi();

      await expect(setSettings({ mainCurrency: 'EUR' }))
        .rejects
        .toThrow('Internal server error');
    });
  });

  describe('getRawSettings', () => {
    it('returns raw settings without UserSettingsModel transformation', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/settings`, () =>
          HttpResponse.json(createSettingsResponse())),
      );

      const { getRawSettings } = useSettingsApi();
      const result = await getRawSettings();

      // Raw settings should have camelCase keys but not be wrapped in model structure
      expect(result).toHaveProperty('mainCurrency');
      expect(result).toHaveProperty('uiFloatingPrecision');
      expect(result).not.toHaveProperty('general');
      expect(result).not.toHaveProperty('accounting');
    });
  });

  describe('backendSettings', () => {
    it('sends GET request to configuration endpoint', async () => {
      let capturedUrl: string | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/settings/configuration`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json(createBackendConfigResponse());
        }),
      );

      const { backendSettings } = useSettingsApi();
      const result = await backendSettings();

      expect(capturedUrl).toBe(`${backendUrl}/api/1/settings/configuration`);
      expect(result.loglevel).toBeDefined();
      expect(result.loglevel.isDefault).toBe(true);
    });

    it('transforms response correctly', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/settings/configuration`, () =>
          HttpResponse.json(createBackendConfigResponse())),
      );

      const { backendSettings } = useSettingsApi();
      const result = await backendSettings();

      // Verify snake_case was converted to camelCase
      expect(result.loglevel.isDefault).toBe(true);
      expect(result.maxLogfilesNum.value).toBe(3);
      expect(result.maxSizeInMbAllLogs.value).toBe(300);
      expect(result.sqliteInstructions.value).toBe(5000);
    });
  });

  describe('updateBackendConfiguration', () => {
    it('sends PUT request with uppercase loglevel', async () => {
      let capturedBody: unknown = null;

      server.use(
        http.put(`${backendUrl}/api/1/settings/configuration`, async ({ request }) => {
          capturedBody = await request.json();
          return HttpResponse.json(createBackendConfigResponse());
        }),
      );

      const { updateBackendConfiguration } = useSettingsApi();
      await updateBackendConfiguration('debug');

      // Verify loglevel is converted to uppercase
      expect(capturedBody).toEqual({
        loglevel: 'DEBUG',
      });
    });

    it('returns parsed BackendConfiguration', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/settings/configuration`, () =>
          HttpResponse.json({
            result: {
              loglevel: { is_default: false, value: 'WARNING' },
              max_logfiles_num: { is_default: true, value: 3 },
              max_size_in_mb_all_logs: { is_default: true, value: 300 },
              sqlite_instructions: { is_default: true, value: 5000 },
            },
            message: '',
          })),
      );

      const { updateBackendConfiguration } = useSettingsApi();
      const result = await updateBackendConfiguration('warning');

      // ActiveLogLevel schema preprocesses to lowercase
      expect(result.loglevel.value).toBe('warning');
      expect(result.loglevel.isDefault).toBe(false);
    });
  });
});
