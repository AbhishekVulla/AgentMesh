import { build, context } from 'esbuild';

const isWatch = process.argv.includes('--watch');
const isProduction = process.argv.includes('--production');

const options = {
  entryPoints: ['src/extension.ts'],
  bundle: true,
  outfile: 'dist/extension.js',
  platform: 'node',
  target: 'node18',
  format: 'cjs',
  external: ['vscode'],
  sourcemap: !isProduction,
  minify: isProduction,
  logLevel: 'info',
};

if (isWatch) {
  const ctx = await context(options);
  await ctx.watch();
  console.log('[esbuild] watching...');
} else {
  await build(options);
  console.log('[esbuild] done');
}
