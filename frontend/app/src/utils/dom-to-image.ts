/* eslint-disable @typescript-eslint/explicit-function-return-type, @stylistic/max-statements-per-line, @typescript-eslint/no-unused-expressions, no-var, vars-on-top, no-void, no-sequences, @typescript-eslint/no-use-before-define, no-cond-assign, block-scoped-var,no-console */
/* prettier-ignore */
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-nocheck
// noinspection JSUnusedGlobalSymbols
// biome-ignore lint: disable
// Copied from: https://github.com/tsayen/dom-to-image

const domtoimage = (function () {
  'use strict';

  async function toSvg(a, b) { function c(a) { return b.bgcolor && (a.style.backgroundColor = b.bgcolor), b.width && (a.style.width = `${b.width}px`), b.height && (a.style.height = `${b.height}px`), b.style && Object.keys(b.style).forEach((c) => { a.style[c] = b.style[c]; }), a; } return b = b || {}, g(b), Promise.resolve(a).then(async a => i(a, b.filter, !0)).then(j).then(k).then(c).then(async c => l(c, b.width || q.width(a), b.height || q.height(a))); }

  async function toPixelData(a, b) { return h(a, b || {}).then(b => b.getContext('2d').getImageData(0, 0, q.width(a), q.height(a)).data); }

  async function toPng(a, b) { return h(a, b || {}).then(a => a.toDataURL()); }

  async function toJpeg(a, b) { return b = b || {}, h(a, b).then(a => a.toDataURL('image/jpeg', b.quality || 1)); }

  async function toBlob(a, b) { return h(a, b || {}).then(q.canvasToBlob); }

  function g(a) { typeof a.imagePlaceholder == 'undefined' ? v.impl.options.imagePlaceholder = u.imagePlaceholder : v.impl.options.imagePlaceholder = a.imagePlaceholder, typeof a.cacheBust == 'undefined' ? v.impl.options.cacheBust = u.cacheBust : v.impl.options.cacheBust = a.cacheBust; }

  async function h(a, c) { function d(a) { const b = document.createElement('canvas'); if (b.width = c.width || q.width(a), b.height = c.height || q.height(a), c.bgcolor) { const d = b.getContext('2d'); d.fillStyle = c.bgcolor, d.fillRect(0, 0, b.width, b.height); } return b; } return toSvg(a, c).then(q.makeImage).then(q.delay(100)).then((b) => { const c = d(a); return c.getContext('2d').drawImage(b, 0, 0), c; }); }

  async function i(a, b, c) {
    function d(a) { return a instanceof HTMLCanvasElement ? q.makeImage(a.toDataURL()) : a.cloneNode(!1); }

    async function e(a, b, c) { async function d(a, b, c) { let d = Promise.resolve(); return b.forEach((b) => { d = d.then(async () => i(b, c)).then((b) => { b && a.appendChild(b); }); }), d; } const e = a.childNodes; return e.length === 0 ? Promise.resolve(b) : d(b, q.asArray(e), c).then(() => b); }

    function f(a, b) {
      function c() { function c(a, b) { function c(a, b) { q.asArray(a).forEach((c) => { b.setProperty(c, a.getPropertyValue(c), a.getPropertyPriority(c)); }); }a.cssText ? b.cssText = a.cssText : c(a, b); }c(window.getComputedStyle(a), b.style); }

      function d() {
        function c(c) {
          function d(a, b, c) {
            function d(a) { const b = a.getPropertyValue('content'); return `${a.cssText} content: ${b};`; }

            function e(a) { function b(b) { return `${b}: ${a.getPropertyValue(b)}${a.getPropertyPriority(b) ? ' !important' : ''}`; } return `${q.asArray(a).map(b).join('; ')};`; } const f = `.${a}:${b}`; const g = c.cssText ? d(c) : e(c); return document.createTextNode(`${f}{${g}}`);
          } const e = window.getComputedStyle(a, c); const f = e.getPropertyValue('content'); if (f !== '' && f !== 'none') { const g = q.uid(); b.className = `${b.className} ${g}`; const h = document.createElement('style'); h.appendChild(d(g, c, e)), b.appendChild(h); }
        }[':before', ':after'].forEach((a) => { c(a); });
      }

      function e() { a instanceof HTMLTextAreaElement && (b.innerHTML = a.value), a instanceof HTMLInputElement && b.setAttribute('value', a.value); }

      function f() { b instanceof SVGElement && (b.setAttribute('xmlns', 'http://www.w3.org/2000/svg'), b instanceof SVGRectElement && ['width', 'height'].forEach((a) => { const c = b.getAttribute(a); c && b.style.setProperty(a, c); })); } return b instanceof Element ? Promise.resolve().then(c).then(d).then(e).then(f).then(() => b) : b;
    } return c || !b || b(a) ? Promise.resolve(a).then(d).then(async c => e(a, c, b)).then(b => f(a, b)) : Promise.resolve();
  }

  async function j(a) { return s.resolveAll().then((b) => { const c = document.createElement('style'); return a.appendChild(c), c.appendChild(document.createTextNode(b)), a; }); }

  function k(a) { return t.inlineAll(a).then(() => a); }

  async function l(a, b, c) { return Promise.resolve(a).then(a => (a.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml'), (new XMLSerializer()).serializeToString(a))).then(q.escapeXhtml).then(a => `<foreignObject x="0" y="0" width="100%" height="100%">${a}</foreignObject>`).then(a => `<svg xmlns="http://www.w3.org/2000/svg" width="${b}" height="${c}">${a}</svg>`).then(a => `data:image/svg+xml;charset=utf-8,${a}`); }

  function m() {
    function a() { const a = 'application/font-woff'; const b = 'image/jpeg'; return { eot: 'application/vnd.ms-fontobject', gif: 'image/gif', jpeg: b, jpg: b, png: 'image/png', svg: 'image/svg+xml', tiff: 'image/tiff', ttf: 'application/font-truetype', woff: a, woff2: a }; }

    function b(a) { const b = /\.([^./]*?)$/g.exec(a); return b ? b[1] : ''; }

    function c(c) { const d = b(c).toLowerCase(); return a()[d] || ''; }

    function d(a) { return a.search(/^(data:)/) !== -1; }

    async function e(a) { return new Promise((b) => { for (var c = window.atob(a.toDataURL().split(',')[1]), d = c.length, e = new Uint8Array(d), f = 0; f < d; f++)e[f] = c.charCodeAt(f); b(new Blob([e], { type: 'image/png' })); }); }

    async function f(a) { return a.toBlob ? new Promise((b) => { a.toBlob(b); }) : e(a); }

    function g(a, b) { const c = document.implementation.createHTMLDocument(); const d = c.createElement('base'); c.head.appendChild(d); const e = c.createElement('a'); return c.body.appendChild(e), d.href = b, e.href = a, e.href; }

    function h() { let a = 0; return function () { function b() { return (`0000${(Math.trunc(Math.random() * 36 ** 4)).toString(36)}`).slice(-4); } return `u${b()}${a++}`; }; }

    async function i(a) { return new Promise((b, c) => { const d = new Image(); d.onload = function () { b(d); }, d.onerror = c, d.src = a; }); }

    async function j(a) {
      const b = 3e4; return v.impl.options.cacheBust && (a += (/\?/.test(a) ? '&' : '?') + Date.now()), new Promise((c) => {
        function d() {
          if (g.readyState === 4) {
            if (g.status !== 200)
              return void (h ? c(h) : f(`cannot fetch resource: ${a}, status: ${g.status}`)); const b = new FileReader(); b.onloadend = function () { const a = b.result.split(/,/)[1]; c(a); }, b.readAsDataURL(g.response);
          }
        }

        function e() { h ? c(h) : f(`timeout of ${b}ms occurred while fetching resource: ${a}`); }

        function f(a) { console.error(a), c(''); } var g = new XMLHttpRequest(); g.onreadystatechange = d, g.ontimeout = e, g.responseType = 'blob', g.timeout = b, g.open('GET', a, !0), g.send(); let h; if (v.impl.options.imagePlaceholder) { const i = v.impl.options.imagePlaceholder.split(/,/); i && i[1] && (h = i[1]); }
      });
    }

    function k(a, b) { return `data:${b};base64,${a}`; }

    function l(a) { return a.replace(/([$()*+./?[\\\]^{|}])/g, '\\$1'); }

    function m(a) { return async function (b) { return new Promise((c) => { setTimeout(() => { c(b); }, a); }); }; }

    function n(a) { for (var b = [], c = a.length, d = 0; d < c; d++)b.push(a[d]); return b; }

    function o(a) { return a.replace(/#/g, '%23').replace(/\n/g, '%0A'); }

    function p(a) { const b = r(a, 'border-left-width'); const c = r(a, 'border-right-width'); return a.scrollWidth + b + c; }

    function q(a) { const b = r(a, 'border-top-width'); const c = r(a, 'border-bottom-width'); return a.scrollHeight + b + c; }

    function r(a, b) { const c = window.getComputedStyle(a).getPropertyValue(b); return parseFloat(c.replace('px', '')); } return { asArray: n, canvasToBlob: f, dataAsUrl: k, delay: m, escape: l, escapeXhtml: o, getAndEncode: j, height: q, isDataUrl: d, makeImage: i, mimeType: c, parseExtension: b, resolveUrl: g, uid: h(), width: p };
  }

  function n() {
    function a(a) { return a.search(e) !== -1; }

    function b(a) { for (var b, c = []; (b = e.exec(a)) !== null;)c.push(b[1]); return c.filter(a => !q.isDataUrl(a)); }

    async function c(a, b, c, d) { function e(a) { return new RegExp(`(url\\(['"]?)(${q.escape(a)})(['"]?\\))`, 'g'); } return Promise.resolve(b).then(a => c ? q.resolveUrl(a, c) : a).then(d || q.getAndEncode).then(a => q.dataAsUrl(a, q.mimeType(b))).then(c => a.replace(e(b), `$1${c}$3`)); }

    async function d(d, e, f) { function g() { return !a(d); } return g() ? Promise.resolve(d) : Promise.resolve(d).then(b).then(async (a) => { let b = Promise.resolve(d); return a.forEach((a) => { b = b.then(async b => c(b, a, e, f)); }), b; }); } var e = /url\(["']?([^"']+?)["']?\)/g; return { impl: { inline: c, readUrls: b }, inlineAll: d, shouldProcess: a };
  }

  function o() {
    async function a() { return b(document).then(async a => Promise.all(a.map(a => a.resolve()))).then(a => a.join('\n')); }

    async function b() {
      function a(a) { return a.filter(a => a.type === CSSRule.FONT_FACE_RULE).filter(a => r.shouldProcess(a.style.getPropertyValue('src'))); }

      function b(a) {
        const b = []; return a.forEach((a) => {
          try { q.asArray(a.cssRules || []).forEach(b.push.bind(b)); }
          catch (error) { console.log(`Error while reading CSS rules from ${a.href}`, error.toString()); }
        }), b;
      }

      function c(a) { return { async resolve() { const b = (a.parentStyleSheet || {}).href; return r.inlineAll(a.cssText, b); }, src() { return a.style.getPropertyValue('src'); } }; } return Promise.resolve(q.asArray(document.styleSheets)).then(b).then(a).then(a => a.map(c));
    } return { impl: { readAll: b }, resolveAll: a };
  }

  function p() {
    function a(a) { async function b(b) { return q.isDataUrl(a.src) ? Promise.resolve() : Promise.resolve(a.src).then(b || q.getAndEncode).then(b => q.dataAsUrl(b, q.mimeType(a.src))).then(async b => new Promise((c, d) => { a.onload = c, a.onerror = d, a.src = b; })); } return { inline: b }; }

    function b(c) { async function d(a) { const b = a.style.getPropertyValue('background'); return b ? r.inlineAll(b).then((b) => { a.style.setProperty('background', b, a.style.getPropertyPriority('background')); }).then(() => a) : Promise.resolve(a); } return c instanceof Element ? d(c).then(() => c instanceof HTMLImageElement ? a(c).inline() : Promise.all(q.asArray(c.childNodes).map(a => b(a)))) : Promise.resolve(c); } return { impl: { newImage: a }, inlineAll: b };
  } var q = m(); var r = n(); var s = o(); var t = p(); var u = { cacheBust: !1, imagePlaceholder: void 0 }; var v = { impl: { fontFaces: s, images: t, inliner: r, options: {}, util: q }, toBlob, toJpeg, toPixelData, toPng, toSvg };

  return v;
})();

export default domtoimage;
