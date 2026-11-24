import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import contract from "@/lib/api/mocks/openapi-emitted.json";
import { IMAGE_REF, IMAGE_REF_WITH_URL } from "@/lib/api/mocks/fixtures";
import { expectNoCriticalA11yViolations } from "@/test/a11y";

import { PageImage } from "./PageImage";

describe("PageImage", () => {
  it("uses image_url from the payload when one is present", () => {
    render(<PageImage image={IMAGE_REF_WITH_URL} />);
    expect(screen.getByRole("img")).toHaveAttribute("src", IMAGE_REF_WITH_URL.image_url ?? "");
    expect(screen.getByRole("img")).toHaveAttribute("alt", IMAGE_REF_WITH_URL.caption ?? "");
  });

  it("falls back to the documented /api/images/{ref_id} route when image_url is absent", () => {
    render(<PageImage image={IMAGE_REF} />);
    expect(screen.getByRole("img")).toHaveAttribute(
      "src",
      `${contract.conventions.images_prefix}${encodeURIComponent(IMAGE_REF.ref_id)}`,
    );
    expect(screen.getByText(IMAGE_REF.caption ?? "")).toBeInTheDocument();
  });

  it("surfaces a failed image load explicitly instead of a broken frame", async () => {
    const { container } = render(<PageImage image={IMAGE_REF} />);
    fireEvent.error(screen.getByRole("img"));
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      `Page image unavailable for reference ${IMAGE_REF.ref_id}.`,
    );
    await expectNoCriticalA11yViolations(container);
  });
});
