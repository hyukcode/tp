import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
  plugins: [vue()],
  build: { outDir: "../template/static", emptyOutDir: true, minify: false },
  server: { proxy: { "/api": "http://127.0.0.1:8765" } },
});
