
import modelOptions from '../config/modelOptions';

export function showDetections(data, canvas) {
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
  const font = "16px helvetica";
  ctx.font = font;
  ctx.textBaseline = "top";

  for (let [key, value] of Object.entries(data)) {
    if (key === 'fps') {
      continue;
    }
    let color = "#2fff00"
    if (key !== "all") {
      color = modelOptions.filter(d => d.id === key)[0].color
    }

    let predictions = value;
    predictions.forEach(prediction => {
      const x = prediction.bbox[0];
      const y = prediction.bbox[1];
      const width = prediction.bbox[2];
      const height = prediction.bbox[3];
      // Draw the bounding box.
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, width, height);
      // Draw the label background.
      ctx.fillStyle = color;
      let score = prediction.score.toFixed(2);
      const textWidth = ctx.measureText(prediction.class+" "+score).width;
      const textHeight = parseInt(font, 10);
      // draw top left rectangle
      ctx.fillRect(x, y, textWidth+5, textHeight+2);
      // draw bottom left rectangle
      //ctx.fillRect(x, y + height - textHeight, textWidth + 15, textHeight + 10);

      // Draw the text last to ensure it's on top.
      ctx.fillStyle = "#000000";
      ctx.fillText(prediction.class+" "+score, x, y+1);
    });
  }

  let fps = data['fps'];
  if (fps) {
    ctx.fillStyle = "#2fff00";
    ctx.lineWidth = 1;
    const textWidth = ctx.measureText("fps: "+fps).width;
    const textHeight = parseInt(font, 10);
    ctx.fillRect(ctx.canvas.width*0.9, ctx.canvas.height*0.025, textWidth+10, textHeight+10);
    ctx.fillStyle = "#000000";
    ctx.fillText("fps: "+fps, ctx.canvas.width*0.9+5, ctx.canvas.height*0.025+5);
  }

}

export function  drawImageProp (ctx, img){

    let x = 0;
    let y = 0;
    let w = ctx.canvas.width;
    let h = ctx.canvas.height;


    // default offset is center
    let offsetX = 0.5;
    let offsetY = 0.5;

    // keep bounds [0.0, 1.0]
    if (offsetX < 0) offsetX = 0;
    if (offsetY < 0) offsetY = 0;
    if (offsetX > 1) offsetX = 1;
    if (offsetY > 1) offsetY = 1;

    var iw = img.width ? img.width : img.videoWidth,
        ih = img.height ? img.height : img.videoHeight,
        r = Math.min(w / iw, h / ih),
        nw = iw * r,   // new prop. width
        nh = ih * r,   // new prop. height
        cx, cy, cw, ch, ar = 1;

    // decide which gap to fill
    if (nw < w) ar = w / nw;
    if (Math.abs(ar - 1) < 1e-14 && nh < h) ar = h / nh;  // updated
    nw *= ar;
    nh *= ar;

    // calc source rectangle
    cw = iw / (nw / w);
    ch = ih / (nh / h);

    cx = (iw - cw) * offsetX;
    cy = (ih - ch) * offsetY;

    // make sure source rectangle is valid
    if (cx < 0) cx = 0;
    if (cy < 0) cy = 0;
    if (cw > iw) cw = iw;
    if (ch > ih) ch = ih;

    // fill image in dest. rectangle
    ctx.drawImage(img, cx, cy, cw, ch,  x, y, w, h);
  }
