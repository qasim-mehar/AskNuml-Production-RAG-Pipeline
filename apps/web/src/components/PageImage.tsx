import type { ImageRef } from "@/lib/api/schemas";

type PageImageProps = {
  image: ImageRef;
};

/** Inline past-paper page image with alt text derived only from payload fields. */
export function PageImage({ image }: PageImageProps) {
  const alt =
    image.caption ??
    `Past-paper page image${image.page !== null && image.page !== undefined ? ` ${image.page}` : ""}`;
  const src = `/api/images/${encodeURIComponent(image.ref_id)}`;

  return (
    <figure className="page-image">
      {/* Object-store pages have no known intrinsic size here; inventing one for
          next/image would fabricate layout data. Native lazy image is honest. */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt={alt} loading="lazy" />
      {image.caption ? <figcaption>{image.caption}</figcaption> : null}
    </figure>
  );
}
