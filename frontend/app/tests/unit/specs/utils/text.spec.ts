import { toHumanReadable, transformCase } from '@rotki/common';
import { describe, expect, it } from 'vitest';

describe('utils/text', () => {
  it('check return value of human readable function', () => {
    expect(toHumanReadable('lorem_ipsum dolor sit_amet')).toEqual('lorem ipsum dolor sit amet');
    expect(toHumanReadable('polygon_pos')).toEqual('polygon pos');
    expect(toHumanReadable('polygon_pos', 'uppercase')).toEqual('POLYGON POS');
    expect(toHumanReadable('polygon_pos', 'capitalize')).toEqual('Polygon Pos');
    expect(toHumanReadable('polygon_POS', 'capitalize')).toEqual('Polygon POS');
    expect(toHumanReadable('polygon_pos', 'sentence')).toEqual('Polygon pos');
    expect(toHumanReadable('POLYGON_POS', 'sentence')).toEqual('POLYGON POS');
    expect(toHumanReadable('polygon_pos', 'lowercase')).toEqual('polygon pos');
    expect(toHumanReadable('POLYGON_POS', 'lowercase')).toEqual('polygon pos');
    expect(toHumanReadable('POLYGON_pos', 'lowercase')).toEqual('polygon pos');
  });

  it('check return value of transform case function', () => {
    expect(transformCase('lorem_ipsum_dolor_sit_amet', true)).toEqual('loremIpsumDolorSitAmet');
    expect(transformCase('lorem_ipsum_dolor_sit_amet')).toEqual('lorem_ipsum_dolor_sit_amet');
    expect(transformCase('loremIpsumDolorSitAmet')).toEqual('lorem_ipsum_dolor_sit_amet');
    expect(transformCase('loremIpsumDolorSitAmet', true)).toEqual('loremIpsumDolorSitAmet');
  });
});
