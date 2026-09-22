import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { buildUrl, ApiError, api, API_BASE } from "@/lib/api";

describe("buildUrl", () => {
  it("prefixes the API base for relative paths", () => {
    expect(buildUrl("/health")).toBe(`${API_BASE}/health`);
  });

  it("adds a leading slash when missing", () => {
    expect(buildUrl("health")).toBe(`${API_BASE}/health`);
  });

  it("serializes scalar query params and skips null/undefined", () => {
    const url = buildUrl("/jobs", { state: "failed", limit: 10, extra: undefined });
    expect(url).toBe(`${API_BASE}/jobs?state=failed&limit=10`);
  });

  it("repeats array params (e.g. graph expand seeds)", () => {
    const url = buildUrl("/graph/expand", { seed: ["INC-1", "INC-2"], hops: 2 });
    expect(url).toBe(`${API_BASE}/graph/expand?seed=INC-1&seed=INC-2&hops=2`);
  });

  it("leaves absolute URLs untouched aside from params", () => {
    expect(buildUrl("http://x/y")).toBe("http://x/y");
  });
});

describe("api client request handling", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockReset();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses JSON success responses", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: "ok" }), { status: 200 }),
    );
    const res = await api.health();
    expect(res).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/health`,
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws ApiError with backend detail on 422", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: "ontology violation" }), {
        status: 422,
      }),
    );
    await expect(
      api.createRelation({ type: "AFFECTED", source_id: "a", target_id: "b" }),
    ).rejects.toMatchObject({ status: 422, message: "ontology violation" });
  });

  it("wraps network failures in an ApiError with status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("failed to fetch"));
    await expect(api.stats()).rejects.toBeInstanceOf(ApiError);
    await expect(api.stats()).rejects.toMatchObject({ status: 0 });
  });

  it("posts seed with reset query param", async () => {
    fetchMock.mockResolvedValue(new Response("{}", { status: 200 }));
    await api.seed(true);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE}/admin/seed?reset=true`,
      expect.objectContaining({ method: "POST" }),
    );
  });
});
