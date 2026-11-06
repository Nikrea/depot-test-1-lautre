// Imprime recompose/livre-recompose.html en PDF A4 (texte vectoriel, polices intégrées).
// Usage : node outils/imprimer.js   (Playwright + Chromium)
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const racine = path.resolve(__dirname, '..');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.join(racine, 'recompose', 'livre-recompose.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForLoadState('networkidle');
  // Ajuste la taille du texte des étapes pour que tout tienne au-dessus des repères nutritionnels.
  const rapport = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll('.etapes-page').forEach((pg) => {
      const etapes = pg.querySelector('.etapes'), limite = pg.querySelector('.reperes').getBoundingClientRect().top - 12;
      let taille = 10.4;
      const deborde = () => [...etapes.children].some((e) => e.getBoundingClientRect().bottom > limite) || etapes.scrollWidth > etapes.clientWidth + 2;
      etapes.style.setProperty('--taille', taille + 'pt');
      while (deborde() && taille > 8.2) { taille -= 0.2; etapes.style.setProperty('--taille', taille.toFixed(1) + 'pt'); }
      out.push(pg.querySelector('h2').textContent.slice(0, 28) + ' → ' + taille.toFixed(1) + 'pt' + (deborde() ? ' DÉBORDE' : ''));
    });
    document.querySelectorAll('.ouverture').forEach((pg) => {
      const note = pg.querySelector('.note-bas'), corps = pg.querySelector('.corps');
      const bas = Math.max(...[...corps.querySelectorAll('.bloc, .frais')].map((e) => e.getBoundingClientRect().bottom));
      const lim = note ? note.getBoundingClientRect().top : pg.getBoundingClientRect().bottom - 60;
      if (bas > lim - 4) out.push('OUVERTURE DÉBORDE : ' + pg.querySelector('h1').textContent);
    });
    return out;
  });
  console.log(rapport.join('\n'));
  await page.pdf({ path: path.join(racine, 'livre-recompose.pdf'), preferCSSPageSize: true, printBackground: true });
  await browser.close();
  console.log('livre-recompose.pdf écrit');
})();
