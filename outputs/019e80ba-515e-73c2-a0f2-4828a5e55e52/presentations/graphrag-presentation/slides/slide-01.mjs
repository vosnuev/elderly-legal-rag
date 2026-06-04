import { addDeckSlide } from "./deck-common.mjs";
export async function slide01(presentation, ctx) {
  return addDeckSlide(presentation, ctx, 1);
}
