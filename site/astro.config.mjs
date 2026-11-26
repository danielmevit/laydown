import { defineConfig } from 'astro/config';

// Served at https://laydown.damt.xyz/ (GitHub Pages custom domain); the old
// danielmevit.github.io/laydown/ address redirects here.
export default defineConfig({
  site: 'https://laydown.damt.xyz',
  base: '/',
});
