"use client";

import { useState } from "react";

import { imageSrcFor } from "@/lib/api/images";
import type { ImageRef } from "@/lib/api/schemas";

type PageImageProps = {
  image: ImageRef;
};

/** Presentational page image: payload URL first, documented route fallback, explicit failure. */
export function PageImage({ image }: PageImageProps) {
  const [failed, setFailed] = useState(false);
  const src = imageSrcFor(image);
  const alt =
    image.caption ??
    `Past-paper page image${image.page !== null && image.page !== undefined ? ` ${image.page}` : ""}`;

  return (
    <figure className="page-image">
      {failed ? (
        <p role="status" className="page-image-error">
          Page image unavailable for reference {image.ref_id}.
        </p>
      ) : (
        // Object-store pages have no known intrinsic size here; inventing one
        // for next/image would fabricate layout data. Native lazy image is honest.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />
      )}
      {image.caption ? <figcaption>{image.caption}</figcaption> : null}
    </figure>
  );
}
