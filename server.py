from flask import Flask, jsonify, abort, make_response, request
from flask_cors import CORS
from threading import Lock
from time import sleep
from utils import base64tocv2, intersection_over_union
import time
import itertools
import heapq
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

frame_buffers = []
models = {}
frameId = 0
model_results = None
reload_queue = None  # send model_names as msg to reload
inf_ready_queue = None
fps_stats = []
app = Flask(__name__)
CORS(app)
reload_model_lock = Lock()


def detect(image, model, frame_id, conf=0.2, iou=0.45, mode="parallel"):
    if frame_buffers[models[model]].full():
        frame_buffers[models[model]].get(False)
    frame_buffers[models[model]].put((frame_id, image, float(conf), float(iou), mode))


def init(api_results, MODELS_IN_USE, frameBuffers, adminQueue, infReadyQueue):
    global models, frame_buffers, model_results, reload_queue, inf_ready_queue
    reload_queue = adminQueue
    inf_ready_queue = infReadyQueue
    for mi, model in enumerate(MODELS_IN_USE):
        models[model[0]] = mi
    frame_buffers.extend(frameBuffers)
    model_results = api_results


def get_fps_stats():
    while fps_stats and fps_stats[0] < time.time() - 1:
        heapq.heappop(fps_stats)
    return len(fps_stats)


def record_fps():
    heapq.heappush(fps_stats, time.time())


@app.route('/detect_objects', methods=['POST'])
def detect_objects():
    global frameId
    if not request.json or 'image' not in request.json:
        abort(400)
    frameId += 1
    image = base64tocv2(request.json['image'])
    response = {}

    for model in request.json['models']:
        conf, iou, model_name = model['conf'], model['iou'], model['model']
        detect(image, model_name, frameId, conf, iou, request.json['mode'])
    return jsonify(response), 201


@app.route('/detect_objects_response', methods=['GET'])
def detect_objects_response():
    global models
    model_names = request.args.get('models', "")
    model_names = model_names.split(",") if model_names else []

    response = {}
    execution_mode = None
    min_t_iou = 1.0
    for model_name in model_names:
        model_index = models[model_name]
        objects_detected = []
        try:
            objects, execution_mode, t_iou = model_results[model_index].get(timeout=1)[1:]
            for obj in objects:
                objects_detected.append({'bbox': [obj.xmin, obj.ymin, obj.xmax - obj.xmin, obj.ymax - obj.ymin],
                                         'class': obj.name, 'score': float(obj.confidence)})
            if t_iou < min_t_iou:
                min_t_iou = t_iou
        except:
            pass
        response[model_name] = objects_detected
    if execution_mode == 'ensemble':
        # Ensemble Detection: Use non-maximum suppression to keep only those detected objects with high confidence
        objects = list(sorted(list(itertools.chain.from_iterable(response.values())),
                              key=lambda obj: obj['score'], reverse=True))
        skip_ids = []
        for i in range(len(objects)):
            for j in range(i + 1, len(objects)):
                if intersection_over_union(objects[i], objects[j]) > min_t_iou:
                    skip_ids.append(j)
        response = {'all': []}
        for i, obj in enumerate(objects):
            if i not in skip_ids:
                response['all'].append(obj)
    if model_names:
        record_fps()
        response["fps"] = get_fps_stats()
    else:
        response["fps"] = None
    return jsonify(response), 201


@app.route('/reload_models', methods=['GET'])
def reload_models():
    with reload_model_lock:
        model_names = request.args.get('models', "")
        model_names = model_names.split(",") if model_names else []
        model_names = [m for m in model_names if m in models]
        if not model_names:
            return
        reload_queue.put(model_names)
        for q in frame_buffers + model_results:
            while not q.empty():
                q.get()
        inf_ready_queue.get()
        sleep(0.5)
    return jsonify(model_names), 201


@app.route('/shutdown', methods=['POST'])
def shutdown():
    global frame_buffers
    global model_results
    shutdown_hook = request.environ.get('werkzeug.server.shutdown')
    for q in frame_buffers + model_results:
        while not q.empty():
            q.get()
    if shutdown_hook is not None:
        shutdown_hook()
    return "", 200


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)
