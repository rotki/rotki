import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountingApi } from './accounting-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/settings/accounting-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useAccountingApi', () => {
    describe('fetchAccountingRules', () => {
      it('sends POST request and returns collection', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    identifier: 1,
                    event_type: 'trade',
                    event_subtype: 'spend',
                    counterparty: null,
                    taxable: { value: true },
                    count_entire_amount_spend: { value: false },
                    count_cost_basis_pnl: { value: true },
                    accounting_treatment: null,
                  },
                ],
                entries_found: 1,
                entries_limit: -1,
                entries_total: 1,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRules } = useAccountingApi();
        const result = await fetchAccountingRules({
          limit: 10,
          offset: 0,
          eventTypes: ['trade'],
        });

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
          event_types: ['trade'],
        });
        expect(result.entries).toHaveLength(1);
        expect(result.entries[0].identifier).toBe(1);
        expect(result.entries[0].eventType).toBe('trade');
      });

      it('sends all optional filter parameters', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: -1,
                entries_total: 0,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRules } = useAccountingApi();
        await fetchAccountingRules({
          limit: 20,
          offset: 5,
          eventTypes: ['trade', 'deposit'],
          eventSubtypes: ['spend', 'receive'],
          counterparties: ['uniswap', null],
          customRuleHandling: true,
          eventIds: [1, 2, 3],
          identifiers: [10, 20],
        });

        expect(capturedBody).toEqual({
          limit: 20,
          offset: 5,
          event_types: ['trade', 'deposit'],
          event_subtypes: ['spend', 'receive'],
          counterparties: ['uniswap', null],
          custom_rule_handling: true,
          event_ids: [1, 2, 3],
          identifiers: [10, 20],
        });
      });

      it('omits orderByAttributes and ascending from payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: -1,
                entries_total: 0,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRules } = useAccountingApi();
        await fetchAccountingRules({
          limit: 10,
          offset: 0,
          orderByAttributes: ['identifier'],
          ascending: [true],
        });

        // orderByAttributes and ascending should be omitted
        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
        });
        expect(capturedBody).not.toHaveProperty('order_by_attributes');
        expect(capturedBody).not.toHaveProperty('ascending');
      });
    });

    describe('fetchAccountingRule', () => {
      it('sends counterparties array with counterparty and null when counterparty is provided', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    identifier: 1,
                    event_type: 'trade',
                    event_subtype: 'spend',
                    counterparty: 'uniswap',
                    taxable: { value: true },
                    count_entire_amount_spend: { value: false },
                    count_cost_basis_pnl: { value: true },
                    accounting_treatment: null,
                  },
                ],
                entries_found: 1,
                entries_limit: -1,
                entries_total: 1,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRule } = useAccountingApi();
        const result = await fetchAccountingRule(
          { limit: 10, offset: 0, eventTypes: ['trade'] },
          'uniswap',
        );

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
          event_types: ['trade'],
          counterparties: ['uniswap', null],
        });
        expect(result).not.toBeNull();
        expect(result?.counterparty).toBe('uniswap');
      });

      it('sends counterparties array with only null when counterparty is null', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: -1,
                entries_total: 0,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRule } = useAccountingApi();
        const result = await fetchAccountingRule(
          { limit: 10, offset: 0 },
          null,
        );

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
          counterparties: [null],
        });
        expect(result).toBeNull();
      });

      it('omits orderByAttributes and ascending from payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: -1,
                entries_total: 0,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRule } = useAccountingApi();
        await fetchAccountingRule(
          { limit: 10, offset: 0, orderByAttributes: ['identifier'], ascending: [true] },
          null,
        );

        expect(capturedBody).not.toHaveProperty('order_by_attributes');
        expect(capturedBody).not.toHaveProperty('ascending');
      });

      it('returns matching counterparty when multiple entries exist', async () => {
        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules`, () =>
            HttpResponse.json({
              result: {
                entries: [
                  {
                    identifier: 1,
                    event_type: 'trade',
                    event_subtype: 'spend',
                    counterparty: null,
                    taxable: { value: true },
                    count_entire_amount_spend: { value: false },
                    count_cost_basis_pnl: { value: true },
                    accounting_treatment: null,
                  },
                  {
                    identifier: 2,
                    event_type: 'trade',
                    event_subtype: 'spend',
                    counterparty: 'uniswap',
                    taxable: { value: false },
                    count_entire_amount_spend: { value: true },
                    count_cost_basis_pnl: { value: false },
                    accounting_treatment: null,
                  },
                ],
                entries_found: 2,
                entries_limit: -1,
                entries_total: 2,
              },
              message: '',
            })),
        );

        const { fetchAccountingRule } = useAccountingApi();
        const result = await fetchAccountingRule(
          { limit: 10, offset: 0 },
          'uniswap',
        );

        expect(result).not.toBeNull();
        expect(result?.identifier).toBe(2);
        expect(result?.counterparty).toBe('uniswap');
      });
    });

    describe('addAccountingRule', () => {
      it('sends PUT request with rule data', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { addAccountingRule } = useAccountingApi();
        const result = await addAccountingRule({
          eventType: 'trade',
          eventSubtype: 'spend',
          counterparty: 'uniswap',
          taxable: { value: true },
          countEntireAmountSpend: { value: false },
          countCostBasisPnl: { value: true },
          accountingTreatment: null,
        });

        expect(capturedBody).toEqual({
          event_type: 'trade',
          event_subtype: 'spend',
          counterparty: 'uniswap',
          taxable: { value: true },
          count_entire_amount_spend: { value: false },
          count_cost_basis_pnl: { value: true },
          accounting_treatment: null,
        });
        expect(result).toBe(true);
      });
    });

    describe('editAccountingRule', () => {
      it('sends PATCH request with rule data including identifier', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { editAccountingRule } = useAccountingApi();
        const result = await editAccountingRule({
          identifier: 1,
          eventType: 'trade',
          eventSubtype: 'spend',
          counterparty: 'uniswap',
          taxable: { value: false },
          countEntireAmountSpend: { value: true },
          countCostBasisPnl: { value: false },
          accountingTreatment: null,
        });

        expect(capturedBody).toEqual({
          identifier: 1,
          event_type: 'trade',
          event_subtype: 'spend',
          counterparty: 'uniswap',
          taxable: { value: false },
          count_entire_amount_spend: { value: true },
          count_cost_basis_pnl: { value: false },
          accounting_treatment: null,
        });
        expect(result).toBe(true);
      });
    });

    describe('deleteAccountingRule', () => {
      it('sends DELETE request with identifier', async () => {
        let capturedBody: unknown;

        server.use(
          http.delete(`${backendUrl}/api/1/accounting/rules`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { deleteAccountingRule } = useAccountingApi();
        const result = await deleteAccountingRule(123);

        expect(capturedBody).toEqual({ identifier: 123 });
        expect(result).toBe(true);
      });
    });

    describe('getAccountingRuleLinkedMapping', () => {
      it('sends GET request and returns mapping', async () => {
        server.use(
          http.get(`${backendUrl}/api/1/accounting/rules/info`, () =>
            HttpResponse.json({
              result: {
                taxable: ['include_crypto2crypto', 'include_gas_costs'],
                count_cost_basis_pnl: ['cost_basis_method'],
              },
              message: '',
            })),
        );

        const { getAccountingRuleLinkedMapping } = useAccountingApi();
        const result = await getAccountingRuleLinkedMapping();

        // Response keys are transformed to camelCase
        expect(result).toEqual({
          taxable: ['include_crypto2crypto', 'include_gas_costs'],
          countCostBasisPnl: ['cost_basis_method'],
        });
      });
    });

    describe('fetchAccountingRuleConflicts', () => {
      it('sends POST request with pagination and returns conflicts collection', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules/conflicts`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [
                  {
                    local_id: 1,
                    local_data: {
                      event_type: 'trade',
                      event_subtype: 'spend',
                      counterparty: null,
                      taxable: { value: true },
                      count_entire_amount_spend: { value: false },
                      count_cost_basis_pnl: { value: true },
                      accounting_treatment: null,
                    },
                    remote_data: {
                      event_type: 'trade',
                      event_subtype: 'spend',
                      counterparty: null,
                      taxable: { value: false },
                      count_entire_amount_spend: { value: true },
                      count_cost_basis_pnl: { value: false },
                      accounting_treatment: null,
                    },
                  },
                ],
                entries_found: 1,
                entries_limit: -1,
                entries_total: 1,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRuleConflicts } = useAccountingApi();
        const result = await fetchAccountingRuleConflicts({
          limit: 10,
          offset: 5,
        });

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 5,
        });
        expect(result.entries).toHaveLength(1);
        expect(result.entries[0].localId).toBe(1);
      });

      it('omits orderByAttributes and ascending from payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules/conflicts`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                entries: [],
                entries_found: 0,
                entries_limit: -1,
                entries_total: 0,
              },
              message: '',
            });
          }),
        );

        const { fetchAccountingRuleConflicts } = useAccountingApi();
        await fetchAccountingRuleConflicts({
          limit: 10,
          offset: 0,
          orderByAttributes: ['localId'],
          ascending: [true],
        });

        expect(capturedBody).toEqual({
          limit: 10,
          offset: 0,
        });
        expect(capturedBody).not.toHaveProperty('order_by_attributes');
        expect(capturedBody).not.toHaveProperty('ascending');
      });
    });

    describe('resolveAccountingRuleConflicts', () => {
      it('sends PATCH request with solveAllUsing resolution', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/accounting/rules/conflicts`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { resolveAccountingRuleConflicts } = useAccountingApi();
        const result = await resolveAccountingRuleConflicts({
          solveAllUsing: 'local',
        });

        expect(capturedBody).toEqual({
          solve_all_using: 'local',
        });
        expect(result).toBe(true);
      });

      it('sends PATCH request with manual conflicts resolution', async () => {
        let capturedBody: unknown;

        server.use(
          http.patch(`${backendUrl}/api/1/accounting/rules/conflicts`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { resolveAccountingRuleConflicts } = useAccountingApi();
        const result = await resolveAccountingRuleConflicts({
          conflicts: [
            { localId: '1', solveUsing: 'local' },
            { localId: '2', solveUsing: 'remote' },
          ],
        });

        expect(capturedBody).toEqual({
          conflicts: [
            { local_id: '1', solve_using: 'local' },
            { local_id: '2', solve_using: 'remote' },
          ],
        });
        expect(result).toBe(true);
      });
    });

    describe('exportAccountingRules', () => {
      it('sends POST request with directoryPath and returns pending task', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules/export`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                task_id: 42,
              },
              message: '',
            });
          }),
        );

        const { exportAccountingRules } = useAccountingApi();
        const result = await exportAccountingRules('/path/to/export');

        expect(capturedBody).toEqual({
          async_query: true,
          directory_path: '/path/to/export',
        });
        expect(result.taskId).toBe(42);
      });

      it('sends POST request without directoryPath when undefined', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/accounting/rules/export`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                task_id: 43,
              },
              message: '',
            });
          }),
        );

        const { exportAccountingRules } = useAccountingApi();
        const result = await exportAccountingRules();

        expect(capturedBody).toEqual({
          async_query: true,
        });
        expect(capturedBody).not.toHaveProperty('directory_path');
        expect(result.taskId).toBe(43);
      });
    });

    describe('importAccountingRulesData', () => {
      it('sends PUT request and returns pending task', async () => {
        let capturedBody: unknown;

        server.use(
          http.put(`${backendUrl}/api/1/accounting/rules/import`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                task_id: 43,
              },
              message: '',
            });
          }),
        );

        const { importAccountingRulesData } = useAccountingApi();
        const result = await importAccountingRulesData('/path/to/import.json');

        expect(capturedBody).toEqual({
          async_query: true,
          filepath: '/path/to/import.json',
        });
        expect(result.taskId).toBe(43);
      });
    });

    describe('uploadAccountingRulesData', () => {
      it('sends PATCH request with FormData containing file and async_query', async () => {
        let contentTypeHeader = '';
        let formData: FormData | null = null;

        server.use(
          http.patch(`${backendUrl}/api/1/accounting/rules/import`, async ({ request }) => {
            contentTypeHeader = request.headers.get('content-type') || '';
            formData = await request.formData();
            return HttpResponse.json({
              result: {
                task_id: 44,
              },
              message: '',
            });
          }),
        );

        const { uploadAccountingRulesData } = useAccountingApi();
        const file = new File(['test content'], 'rules.json', { type: 'application/json' });
        const result = await uploadAccountingRulesData(file);

        expect(contentTypeHeader).toContain('multipart/form-data');
        expect(formData).not.toBeNull();
        expect(formData!.get('filepath')).toBeInstanceOf(File);
        expect((formData!.get('filepath') as File).name).toBe('rules.json');
        expect(formData!.get('async_query')).toBe('true');
        expect(result.taskId).toBe(44);
      });
    });
  });
});
