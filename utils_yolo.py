# utils_yolo.py contains all functions or classes that are needed to parse the raw outputs obtained from the detector.
# It is recommended to maintain one utils.py per detection algorithm even if some functions are overlapped.
# The parser below is modified from OpenCV:
# https://github.com/opencv/open_model_zoo/blob/master/demos/python_demos/object_detection_demo_yolov3_async/object_detection_demo_yolov3_async.py
from utils import DetectedObject
import math


def YOLOv3_ParseOutput(net, outputs, resized_image_shape, original_image_shape, class_names, t_conf=0.50, t_iou=0.40):
    objects = list()
    for layer_name, out_blob in outputs.items():
        out_blob = out_blob.reshape(net.layers[net.layers[layer_name].parents[0]].shape)
        layer_params = YOLOv3_Params(net.layers[layer_name].params, out_blob.shape[2])
        objects += YOLOv3_ParseRegion(out_blob, resized_image_shape, original_image_shape, layer_params, t_conf)

    objects = sorted(objects, key=lambda obj: obj['confidence'], reverse=True)
    for i in range(len(objects)):
        if objects[i]['confidence'] < t_conf:
            continue
        for j in range(i + 1, len(objects)):
            if YOLOv3_IOU(objects[i], objects[j]) > t_iou:
                objects[j]['confidence'] = 0

    objects_c = []
    for obj in objects:
        if obj['confidence'] >= t_conf:
            x_min, y_min = max(obj['xmin'], 0), max(obj['ymin'], 0)
            x_max, y_max = min(obj['xmax'], original_image_shape[1]), min(obj['ymax'], original_image_shape[0])
            W, H = x_max - x_min, y_max - y_min
            x, y = x_min + W / 2., y_min + H / 2.
            objects_c.append(DetectedObject(x, y, H, W, obj['class_id'], obj['confidence'], 1., 1., class_names))
    return objects_c


class YOLOv3_Params:
    def __init__(self, param, side):
        self.num = int(param['num'])
        self.coords = int(param['coords'])
        self.classes = int(param['classes'])
        self.anchors = [float(a) for a in param['anchors'].split(',')]

        if 'mask' in param:
            mask = [int(idx) for idx in param['mask'].split(',')]
            self.num = len(mask)

            maskedAnchors = []
            for idx in mask:
                maskedAnchors += [self.anchors[idx * 2], self.anchors[idx * 2 + 1]]
            self.anchors = maskedAnchors

        self.side = side
        self.isYOLOv3 = 'mask' in param  # Weak way to determine but the only one.


def YOLOv3_ParseRegion(blob, resized_image_shape, original_im_shape, params, threshold):
    _, _, out_blob_h, out_blob_w = blob.shape
    assert out_blob_w == out_blob_h, "Invalid size of output blob. It sould be in NCHW layout and height should " \
                                     "be equal to width. Current height = {}, current width = {}" \
                                     "".format(out_blob_h, out_blob_w)
    orig_im_h, orig_im_w = original_im_shape
    resized_image_h, resized_image_w = resized_image_shape
    objects = list()
    predictions = blob.flatten()
    side_square = params.side * params.side

    for i in range(side_square):
        row = i // params.side
        col = i % params.side
        for n in range(params.num):
            obj_index = YOLOv3_EntryIndex(params.side, params.coords, params.classes,
                                          n * side_square + i, params.coords)
            scale = predictions[obj_index]
            if scale < threshold:
                continue
            box_index = YOLOv3_EntryIndex(params.side, params.coords, params.classes, n * side_square + i, 0)
            x = (col + predictions[box_index + 0 * side_square]) / params.side
            y = (row + predictions[box_index + 1 * side_square]) / params.side
            try:
                w_exp = math.exp(predictions[box_index + 2 * side_square])
                h_exp = math.exp(predictions[box_index + 3 * side_square])
            except OverflowError:
                continue
            w = w_exp * params.anchors[2 * n] / (resized_image_w if params.isYOLOv3 else params.side)
            h = h_exp * params.anchors[2 * n + 1] / (resized_image_h if params.isYOLOv3 else params.side)
            for j in range(params.classes):
                class_index = YOLOv3_EntryIndex(params.side, params.coords, params.classes, n * side_square + i,
                                                params.coords + 1 + j)
                confidence = scale * predictions[class_index]
                if confidence < threshold:
                    continue
                objects.append(YOLOv3_ScaleBbox(x=x, y=y, h=h, w=w, class_id=j, confidence=confidence,
                                                h_scale=orig_im_h, w_scale=orig_im_w))
    return objects


def YOLOv3_EntryIndex(side, coord, classes, location, entry):
    side_power_2 = side ** 2
    n = location // side_power_2
    loc = location % side_power_2
    return int(side_power_2 * (n * (coord + classes + 1) + entry) + loc)


def YOLOv3_ScaleBbox(x, y, h, w, class_id, confidence, h_scale, w_scale):
    xmin = int((x - w / 2) * w_scale)
    ymin = int((y - h / 2) * h_scale)
    xmax = int(xmin + w * w_scale)
    ymax = int(ymin + h * h_scale)
    return dict(xmin=xmin, xmax=xmax, ymin=ymin, ymax=ymax, class_id=class_id, confidence=confidence)


def YOLOv3_IOU(box_1, box_2):
    width_of_overlap_area = min(box_1['xmax'], box_2['xmax']) - max(box_1['xmin'], box_2['xmin'])
    height_of_overlap_area = min(box_1['ymax'], box_2['ymax']) - max(box_1['ymin'], box_2['ymin'])
    if width_of_overlap_area < 0 or height_of_overlap_area < 0:
        area_of_overlap = 0
    else:
        area_of_overlap = width_of_overlap_area * height_of_overlap_area
    box_1_area = (box_1['ymax'] - box_1['ymin']) * (box_1['xmax'] - box_1['xmin'])
    box_2_area = (box_2['ymax'] - box_2['ymin']) * (box_2['xmax'] - box_2['xmin'])
    area_of_union = box_1_area + box_2_area - area_of_overlap
    if area_of_union == 0:
        return 0
    return area_of_overlap / area_of_union
