import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MessageBubble } from "./MessageBubble";

describe("MessageBubble", () => {
  it("sets RTL direction and the Urdu language tag for Urdu text", () => {
    const { container } = render(
      <MessageBubble text="یہ اردو جواب ہے۔" language="ur" />,
    );
    const bubble = container.querySelector("article");
    expect(bubble).toHaveAttribute("dir", "rtl");
    expect(bubble).toHaveAttribute("lang", "ur");
  });

  it("keeps each run's direction in a mixed English/Urdu message", () => {
    const { container } = render(
      <MessageBubble text="Fee is ready — فیس تیار ہے۔" language="ur" />,
    );
    const runs = Array.from(container.querySelectorAll("article span"));
    expect(runs.map((run) => run.getAttribute("dir"))).toEqual(["ltr", "rtl"]);
    expect(runs[0]).toHaveAttribute("lang", "en");
    expect(runs[1]).toHaveAttribute("lang", "ur");
  });

  it("renders Roman Urdu left-to-right with a Latin-script language tag", () => {
    const { container } = render(
      <MessageBubble text="CS ki fee 1000 hai." language="roman_urdu" />,
    );
    expect(container.querySelector("article")).toHaveAttribute("dir", "ltr");
    expect(container.querySelector("article")).toHaveAttribute("lang", "ur-Latn");
    expect(container.querySelector("article span")).toHaveAttribute("lang", "ur-Latn");
  });
});
