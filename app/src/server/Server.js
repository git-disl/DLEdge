
var generator="";

function *pollForResult(){
  var models = yield [];
  while (true) {
    yield fetch('http://localhost:5000/detect_objects_response?models='+Array.from(models).toString(), {method:'get'})
          .then(res => {return res.json()});
  }
}



var wrapper = function(models) {
  return new Promise(function(resolve, reject) {
    let p = generator.next(models);
    p.value.then(res => {
      if (!res || res.length===0) {
        setTimeout(()=> {return wrapper(models)}, 1000);
      } else {
        resolve(res);
      }
    });
  })
}

export function getPredictions(image, mode, models, config) {
  let modelConfigs = [];
  models.forEach(model => {
    modelConfigs.push({
      model: model,
      conf: config[model].conf,
      iou: config[model].iou
    });
  });
  generator = pollForResult();
  generator.next();

  return fetch("http://localhost:5000/detect_objects", {
           method: 'POST',
           headers: {
               'Content-Type': 'application/json'
           },
           body:JSON.stringify({
             image:image,
             mode: mode,
             models: modelConfigs
           })
       })
       .then(res => {
         if (res.status === 201 || res.status===200) {
           return wrapper(models);
         }

       })
}
