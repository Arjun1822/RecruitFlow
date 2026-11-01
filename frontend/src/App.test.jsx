import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { Login } from "./App";

describe("RecruitFlow frontend", () => {
  it("renders the sign-in boundary without a development token", () => {
    expect(renderToStaticMarkup(<Login onLogin={() => {}} />)).toContain("Sign in");
  });
});
