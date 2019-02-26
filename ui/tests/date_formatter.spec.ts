import {DateFormatter} from '../date_formatter';
import * as chai from 'chai';

chai.should();

describe('DateFormatter', function () {
    const converter = new DateFormatter();
    let date: Date;
    let originalOffset:  () => number;

    function overrideTimezoneOffset(offset: number) {
        Date.prototype.getTimezoneOffset = () => offset;
    }

    beforeEach(function () {
        process.env.TZ='UTC';
        originalOffset = Date.prototype.getTimezoneOffset;
        overrideTimezoneOffset(0);
        date = new Date(Date.parse('03 Feb 2019 13:09:09 UTC'));
    });

    afterEach(function () {
        Date.prototype.getTimezoneOffset = originalOffset;
    });

    it('should return the day in short form if the pattern is %a', function () {
        converter.format(date, '%a').should.equal('Sun');
    });

    it('should return the day in long form if the pattern is %A', function () {
        converter.format(date, '%A').should.equal('Sunday');
    });

    it('should return the day in numeric if the pattern is %w', function () {
        converter.format(date, '%w').should.equal('0');
    });

    it('should return the year in 2-digit format if the pattern is %y', function () {
        converter.format(date, '%y').should.equal('19');
    });

    it('should return the year in full format if the pattern is %Y', function () {
        converter.format(date, '%Y').should.equal('2019');
    });

    it('should return the month in short format if the pattern is %b', function () {
        converter.format(date, '%b').should.equal('Feb');
    });

    it('should return the month in full format if the pattern is %B', function () {
        converter.format(date, '%B').should.equal('February');
    });

    it('should return the month in 2-digit format if the pattern is %m', function () {
        converter.format(date, '%m').should.equal('02');
    });

    it('should return the month in numeric format if the pattern is %-m', function () {
        converter.format(date, '%-m').should.equal('2');
    });

    it('should return the day in 2-digit format if the pattern is %d', function () {
        converter.format(date, '%d').should.equal('03');
    });

    it('should return the day in numeric format if the pattern is %-d', function () {
        converter.format(date, '%-d').should.equal('3');
    });

    it('should return the hour in 2-digit format if the pattern is %H', function () {
        date.setHours(8);
        converter.format(date, '%H').should.equal('08');
    });

    it('should return the hour in numeric format if the pattern is %-H', function () {
        date.setHours(8);
        converter.format(date, '%-H').should.equal('8');
    });

    it('should return the hours in 12-hour 2-digit format if the pattern is %I', function () {
        converter.format(date, '%I').should.equal('01');
    });

    it('should return the hours in 12-hour numeric format if the pattern is %-I', function () {
        converter.format(date, '%-I').should.equal('1');
    });

    it('should return the minutes in 2-digit format if the pattern is %M', function () {
        converter.format(date, '%M').should.equal('09');
    });

    it('should return the minutes in numeric format if the pattern is %-M', function () {
        converter.format(date, '%-M').should.equal('9');
    });

    it('should return the seconds in 2-digit format if the pattern is %S', function () {
        converter.format(date, '%S').should.equal('09');
    });

    it('should return the seconds in numeric format if the pattern is %-S', function () {
        converter.format(date, '%-S').should.equal('9');
    });

    it('should return the am/pm if the pattern is %p', function () {
        converter.format(date, '%p').should.equal('PM');
        date.setTime(8);
        converter.format(date, '%p').should.equal('AM');
    });

    it('should return the timezone if the pattern is %z', function () {
        converter.format(date, '%z').should.equal('+0000');
        overrideTimezoneOffset(+120);
        converter.format(new Date('2019-02-03T13:09:09-02:00'), '%z').should.equal('-0200');
    });

    it('should return the timezone if the pattern is %Z', function () {
        converter.format(date, '%Z').should.be.oneOf(['UTC', 'GMT']);
    });

    it('should return the day of the year padded if the pattern is %j', function () {
        converter.format(date, '%j').should.equal('034');
    });

    it('should return the day of the year if the pattern is %-j', function () {
        converter.format(date, '%-j').should.equal('34');
    });

    it('should return the locale’s appropriate date and time representation if the pattern is %c', function () {
        converter.format(date, '%c').should.equal('2/3/2019, 1:09:09 PM');
    });

    it('should return the locale’s appropriate date representation if the pattern is %x', function () {
        converter.format(date, '%x').should.equal('2/3/2019');
    });

    it('should return the locale’s appropriate time representation if the pattern is %X', function () {
        converter.format(date, '%X').should.equal('1:09:09 PM');
    });
});
