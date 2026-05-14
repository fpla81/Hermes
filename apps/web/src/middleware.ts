export { auth as middleware } from "@/lib/auth";

export const config = {
  matcher: ["/cases/:path*", "/fundamentos/:path*", "/templates/:path*", "/settings/:path*"],
};
