import { CSVMissingHeadersError, useCsvImportExport } from '@/composables/common/use-csv-import-export';
import { describe, expect, it } from 'vitest';

describe('useCsvImportExport', () => {
  describe('parseCSV', () => {
    it('should throw an exception when required headers are not', () => {
      const csv = `
    address,label,tags
    0x123,me,tag1;tag2
    `.trim();
      const { parseCSV } = useCsvImportExport();
      expect(() => parseCSV(csv, {
        requiredHeaders: ['chain', 'address'],
      })).toThrow(CSVMissingHeadersError);
    });

    it('should parse a valid csv', () => {
      const csv = `
    address,chain,label,tags
    0x123,eth,me,tag1;tag2
    `.trim();

      const { parseCSV } = useCsvImportExport();

      expect(parseCSV(csv, {
        requiredHeaders: ['chain', 'address'],
      })).toMatchObject([{
        address: '0x123',
        chain: 'eth',
        tags: 'tag1;tag2',
      }]);
    });

    it('should transform csv headers to camelCase', () => {
      const csv = `
    address,chain,label,tags,ownership percentage
    0x123,eth,me,tag1;tag2,100
    `.trim();

      const { parseCSV } = useCsvImportExport();
      expect(parseCSV(csv)).toMatchObject([{
        address: '0x123',
        chain: 'eth',
        ownershipPercentage: '100',
        tags: 'tag1;tag2',
      }]);
    });
  });

  describe('generateCSV', () => {
    it('should generate a csv out of an object', () => {
      const data = [{
        address: '0x123',
        chain: 'eth',
        label: 'me',
        tags: 'tag1;tag2',
      }];

      const { generateCSV } = useCsvImportExport();

      expect(generateCSV(data)).toEqual(`address,chain,label,tags\n0x123,eth,me,tag1;tag2`);
    });

    it('should use serializers if they exist', () => {
      const data = [{
        address: '0x123',
        chain: 'eth',
        label: 'me',
        tags: ['tag1', 'tag2'],
      }];

      const { generateCSV } = useCsvImportExport();

      expect(generateCSV(data, {
        serializers: {
          tags: (tags: string[]): string => tags.join(';'),
        },
      })).toEqual(`address,chain,label,tags\n0x123,eth,me,tag1;tag2`);
    });

    it('should add a space in a header on camelCase', () => {
      const data = [{
        address: '0x123',
        chain: 'eth',
        label: 'me',
        ownershipPercentage: '100',
        tags: ['tag1', 'tag2'],
      }];

      const { generateCSV } = useCsvImportExport();

      expect(generateCSV(data, {
        serializers: {
          tags: (tags: string[]): string => tags.join(';'),
        },
      })).toEqual(`address,chain,label,ownership percentage,tags\n0x123,eth,me,100,tag1;tag2`);
    });
  });
});
