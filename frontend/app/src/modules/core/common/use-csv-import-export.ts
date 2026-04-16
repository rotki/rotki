import { camelCase, lowerCase } from 'es-toolkit';

export class CSVMissingHeadersError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'CSVMissingHeadersError';
  }
}

interface CSVImportExportParams {
  columnDelimiter?: string;
  rowDelimiter?: string;
}

interface CSVImportParams {
  requiredHeaders?: string[];
}

interface CSVExportParams {
  serializers?: Record<string, (value: any) => string>;
}

interface CSVRow { [key: string]: string }

interface CSVImportRow { [key: string]: any }

interface UseCSVImportExportReturn {
  generateCSV: (data: Array<CSVImportRow>, params?: CSVExportParams) => string;
  parseCSV: (text: string, params?: CSVImportParams) => Array<CSVRow>;
}

export function useCsvImportExport(params: CSVImportExportParams = {}): UseCSVImportExportReturn {
  const { columnDelimiter = ',', rowDelimiter = '\n' } = params;

  function parseCSV(text: string, params: CSVImportParams = {}): Array<CSVRow> {
    const { requiredHeaders = [] } = params;
    const lines = text.trim().split(rowDelimiter);
    const headers = lines[0].split(columnDelimiter);

    if (!requiredHeaders.every(header => headers.includes(header))) {
      throw new CSVMissingHeadersError(`Expected headers ${requiredHeaders.join(',')} to be present, got ${headers.join(',')}`);
    }

    return lines.slice(1).map((line) => {
      const values = line.split(columnDelimiter);
      const row: CSVRow = {};

      headers.forEach((header, index) => {
        row[camelCase(header.trim())] = values[index].trim();
      });

      return row;
    });
  }

  function generateCSV(data: Array<CSVImportRow>, params: CSVExportParams = {}): string {
    if (data.length === 0)
      return '';

    const { serializers } = params;

    const headers = Object.keys(data[0]);
    const csvLines = [headers.map(header => lowerCase(header)).join(columnDelimiter)];
    data.forEach((row) => {
      const values = headers.map((header) => {
        const value = row[header];
        return serializers?.[header]?.(value) ?? value;
      });
      csvLines.push(values.join(columnDelimiter));
    });

    return csvLines.join(rowDelimiter);
  }

  return {
    generateCSV,
    parseCSV,
  };
}
