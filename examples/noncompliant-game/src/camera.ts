import * as faceapi from "face-api.js";
export async function mood(video) {
  const r = await faceapi.detectAllFaces(video).withFaceExpressions();
  return r;
}
