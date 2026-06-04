import { addDeckSlide } from "./deck-common.mjs";
export async function slide02(presentation, ctx) {
  return addDeckSlide(presentation, ctx, 2);
}
