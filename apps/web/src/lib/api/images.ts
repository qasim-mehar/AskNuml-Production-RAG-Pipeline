/** Pure image-source resolution. No React, no fetching. */

import type { ImageRef } from "./schemas";
import { imageRouteFor } from "./routes";

/**
 * Use the payload's `image_url` when it carries one; otherwise fall back to the
 * ADR 0007 `/api/images/{ref_id}` convention. No URL is invented beyond that
 * documented fallback.
 */
export function imageSrcFor(image: ImageRef): string {
  return image.image_url && image.image_url.trim() !== ""
    ? image.image_url
    : imageRouteFor(image.ref_id);
}
