import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import preact from '@astrojs/preact';

// SITE_URL is set per environment (domain not chosen yet). || not ??: CI passes an empty string when the variable is unset.
const site = process.env.SITE_URL || 'http://localhost:4321';

export default defineConfig({
  site,
  output: 'static',
  integrations: [mdx(), preact()],
});
