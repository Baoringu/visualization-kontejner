import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({ baseUrl: process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000", credentials: "include" });

api.use({
  async onRequest({ request }) {
    if (!(["GET", "HEAD", "OPTIONS"].includes(request.method))) {
      const token = document.cookie.split("; ").find((part) => part.startsWith("pallet_building_csrf="))?.split("=")[1];
      if (token) request.headers.set("X-CSRF-Token", decodeURIComponent(token));
    }
    return request;
  },
});
