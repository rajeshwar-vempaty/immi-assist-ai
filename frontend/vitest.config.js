import { defineConfig } from "vitest/config";

// page.js / layout.js contain JSX in .js files (Next.js convention). Vite's
// esbuild excludes .js from transformation by default, so widen the filter and
// use the automatic JSX runtime (no explicit React import needed).
export default defineConfig({
  esbuild: {
    loader: "jsx",
    jsx: "automatic",
    include: /\.[jt]sx?$/,
    exclude: /node_modules/,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.js"],
    include: ["**/*.{test,spec}.{js,jsx}"],
    exclude: ["node_modules", ".next", "dist"],
    coverage: {
      provider: "v8",
      include: ["lib/**/*.js", "app/**/*.js"],
      reporter: ["text", "html"],
    },
  },
});
