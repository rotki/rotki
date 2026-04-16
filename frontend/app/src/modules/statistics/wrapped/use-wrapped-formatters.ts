import dayjs from 'dayjs';

interface UseWrappedFormattersReturn {
  calculateFontSize: (symbol: string) => string;
  formatDate: (timestamp: number) => string;
  hasSectionData: (data: Record<string, any> | Array<any> | undefined) => boolean;
}

export function useWrappedFormatters(): UseWrappedFormattersReturn {
  function hasSectionData(data: Record<string, any> | Array<any> | undefined): boolean {
    if (!data)
      return false;
    if (Array.isArray(data))
      return data.length > 0;
    return Object.keys(data).length > 0;
  }

  function formatDate(timestamp: number): string {
    return dayjs(timestamp * 1000).format('dddd, MMMM D, YYYY');
  }

  function calculateFontSize(symbol: string): string {
    const length = symbol.length;
    return `${1.8 - length * 0.4}em`;
  }

  return {
    calculateFontSize,
    formatDate,
    hasSectionData,
  };
}
