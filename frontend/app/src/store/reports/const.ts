import { ReportPeriod } from '@/store/reports/types';

export const emptyPeriod: () => ReportPeriod = () => ({
  start: 0,
  end: 0
});
