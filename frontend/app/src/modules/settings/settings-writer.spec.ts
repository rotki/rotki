import { TimeFramePeriod } from '@rotki/common';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Currency } from '@/modules/assets/amount-display/currencies';
import { Module } from '@/modules/core/common/modules';
import { useSettingsWriter } from '@/modules/settings/settings-writer';
import { CostBasisMethod } from '@/modules/settings/types/user-settings';

const mockUpdate = vi.fn(async (): Promise<{ success: boolean; message?: string }> => ({ success: true }));
const mockUpdateFrontendSetting = vi.fn(async (): Promise<{ success: boolean; message?: string }> => ({ success: true }));
const mockUpdateSession = vi.fn((): { success: boolean } => ({ success: true }));
const mockSetAnimationsEnabled = vi.fn();

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: vi.fn((): Record<string, unknown> => ({
    update: mockUpdate,
    updateFrontendSetting: mockUpdateFrontendSetting,
  })),
}));

vi.mock('@/modules/settings/settings-repo', () => ({
  useSettingsRepo: vi.fn((): Record<string, unknown> => ({
    setAnimationsEnabled: mockSetAnimationsEnabled,
    updateSession: mockUpdateSession,
  })),
}));

describe('useSettingsWriter', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('write', () => {
    it('should route a general key through update with its own wire key', async () => {
      const { write } = useSettingsWriter();
      await write('activeModules', [Module.MAKERDAO_DSR]);
      expect(mockUpdate).toHaveBeenCalledWith({ activeModules: [Module.MAKERDAO_DSR] });
    });

    it('should route an accounting key through update', async () => {
      const { write } = useSettingsWriter();
      await write('costBasisMethod', CostBasisMethod.FIFO);
      expect(mockUpdate).toHaveBeenCalledWith({ costBasisMethod: CostBasisMethod.FIFO });
    });

    it('should rename and encode currency to mainCurrency ticker', async () => {
      const { write } = useSettingsWriter();
      await write('currency', new Currency('Euro', 'EUR', '€'));
      expect(mockUpdate).toHaveBeenCalledWith({ mainCurrency: 'EUR' });
    });

    it('should rename floatingPrecision to uiFloatingPrecision', async () => {
      const { write } = useSettingsWriter();
      await write('floatingPrecision', 4);
      expect(mockUpdate).toHaveBeenCalledWith({ uiFloatingPrecision: 4 });
    });

    it('should route a frontend key through updateFrontendSetting', async () => {
      const { write } = useSettingsWriter();
      await write('itemsPerPage', 25);
      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ itemsPerPage: 25 });
      expect(mockUpdate).not.toHaveBeenCalled();
    });

    it('should route a session key through the session store update', async () => {
      const { write } = useSettingsWriter();
      await write('timeframe', TimeFramePeriod.ALL);
      expect(mockUpdateSession).toHaveBeenCalledWith({ timeframe: TimeFramePeriod.ALL });
    });

    it('should route animationsEnabled through its dedicated setter', async () => {
      const { write } = useSettingsWriter();
      await write('animationsEnabled', false);
      expect(mockSetAnimationsEnabled).toHaveBeenCalledWith(false);
      expect(mockUpdateSession).not.toHaveBeenCalled();
    });

    it('should surface a write failure', async () => {
      mockUpdate.mockResolvedValueOnce({ message: 'boom', success: false });
      const { write } = useSettingsWriter();
      const result = await write('activeModules', []);
      expect(result).toStrictEqual({ message: 'boom', success: false });
    });
  });

  describe('writeMany', () => {
    it('should batch one call per channel', async () => {
      const { writeMany } = useSettingsWriter();
      await writeMany({
        currency: new Currency('US Dollar', 'USD', '$'),
        floatingPrecision: 2,
        itemsPerPage: 50,
        timeframe: TimeFramePeriod.WEEK,
      });
      expect(mockUpdate).toHaveBeenCalledOnce();
      expect(mockUpdate).toHaveBeenCalledWith({ mainCurrency: 'USD', uiFloatingPrecision: 2 });
      expect(mockUpdateFrontendSetting).toHaveBeenCalledOnce();
      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ itemsPerPage: 50 });
      expect(mockUpdateSession).toHaveBeenCalledWith({ timeframe: TimeFramePeriod.WEEK });
    });

    it('should route animationsEnabled separately within a batch', async () => {
      const { writeMany } = useSettingsWriter();
      await writeMany({ animationsEnabled: true, itemsPerPage: 10 });
      expect(mockSetAnimationsEnabled).toHaveBeenCalledWith(true);
      expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({ itemsPerPage: 10 });
      expect(mockUpdateSession).not.toHaveBeenCalled();
    });

    it('should return the first failure', async () => {
      mockUpdateFrontendSetting.mockResolvedValueOnce({ message: 'nope', success: false });
      const { writeMany } = useSettingsWriter();
      const result = await writeMany({ itemsPerPage: 10 });
      expect(result).toStrictEqual({ message: 'nope', success: false });
    });

    it('should skip channels with no keys', async () => {
      const { writeMany } = useSettingsWriter();
      await writeMany({ itemsPerPage: 10 });
      expect(mockUpdate).not.toHaveBeenCalled();
      expect(mockUpdateSession).not.toHaveBeenCalled();
    });
  });
});
