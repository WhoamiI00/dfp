import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Pin Turbopack's project root to the web-app directory. Without this,
  // Next.js sees lockfiles in both this dir and the repo root (where the
  // root package.json with run scripts lives) and picks the wrong one.
  turbopack: {
    root: path.resolve(__dirname),
  },
};

export default nextConfig;
