import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { IMAGE_REF } from "@/lib/api/mocks/fixtures";

import { PageImage } from "./PageImage";

describe("PageImage", () => {
  it("uses the payload caption as alt text and resolves the ref through the image endpoint", () => {
    render(<PageImage image={IMAGE_REF} />);
    expect(screen.getByRole("img")).toHaveAttribute("alt", IMAGE_REF.caption ?? "");
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      `/api/images/${encodeURIComponent(IMAGE_REF.ref_id)}`,
    );
    expect(screen.getByText(IMAGE_REF.caption ?? "")).toBeInTheDocument();
  });
});
