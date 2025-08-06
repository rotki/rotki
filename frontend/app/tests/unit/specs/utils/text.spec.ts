import {
  getTextToken,
  toCapitalCase,
  toHumanReadable,
  toSentenceCase,
  toSnakeCase,
  transformCase,
} from '@rotki/common';
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

  it('check return value of toSentenceCase function', () => {
    expect(toSentenceCase('this is a sentence')).toEqual('This is a sentence');
    expect(toSentenceCase('HELLO WORLD')).toEqual('HELLO WORLD');
    expect(toSentenceCase('hello')).toEqual('Hello');
    expect(toSentenceCase('h')).toEqual('H');
    expect(toSentenceCase('')).toEqual('');
    expect(toSentenceCase('123 numbers')).toEqual('123 numbers');
  });

  it('check return value of getTextToken function', () => {
    expect(getTextToken('this is a sentence')).toEqual('thisisasentence');
    expect(getTextToken('Hello World!')).toEqual('helloworld');
    expect(getTextToken('Test-123_abc')).toEqual('test123abc');
    expect(getTextToken('  SPACED  ')).toEqual('spaced');
    expect(getTextToken('special!@#$%^&*()chars')).toEqual('specialchars');
    expect(getTextToken('')).toEqual('');
    expect(getTextToken('123abc456')).toEqual('123abc456');
  });

  it('check return value of toSnakeCase function', () => {
    expect(toSnakeCase('thisIsAString')).toEqual('this_is_a_string');
    expect(toSnakeCase('ThisIsAString')).toEqual('this_is_a_string');
    expect(toSnakeCase('this is a sentence')).toEqual('this_is_a_sentence');
    expect(toSnakeCase('CONSTANT_CASE')).toEqual('c_o_n_s_t_a_n_t__c_a_s_e');
    expect(toSnakeCase('mixedCase123')).toEqual('mixed_case123');
    expect(toSnakeCase('')).toEqual('');
    expect(toSnakeCase('already_snake_case')).toEqual('already_snake_case');
  });

  it('check return value of toCapitalCase function', () => {
    expect(toCapitalCase('this is a sentence')).toEqual('This Is A Sentence');
    expect(toCapitalCase('hello world')).toEqual('Hello World');
    expect(toCapitalCase('it\'s a test')).toEqual('It\'s A Test');
    expect(toCapitalCase('ALREADY CAPS')).toEqual('ALREADY CAPS');
    expect(toCapitalCase('mixed CASE text')).toEqual('Mixed CASE Text');
    expect(toCapitalCase('123 numbers here')).toEqual('123 Numbers Here');
    expect(toCapitalCase('')).toEqual('');
  });
});
