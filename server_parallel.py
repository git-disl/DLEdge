from openvino.inference_engine import IENetwork, IEPlugin
from time import sleep
from utils import *
from utils_yolo import *
import multiprocessing as mp
import numpy as np
import threading
import argparse
import heapq
import sys
import cv2

parser = argparse.ArgumentParser()
parser.add_argument('-numncs', '--number_of_ncs', dest='number_of_ncs', type=int, default=1,
                    help='Number of NCS. (Default=1)')
args = parser.parse_args()
number_of_ncs = args.number_of_ncs  # TODO: Support numncs=0 ==> CPU mode
assert number_of_ncs > 0, "You should use at least one Intel Neural Compute Stick 2 to run this project."

# Current version supports ten tiny-YOLOv3 trained on PASCAL VOC with different input sizes (see the folder "models")
# TODO: Read the list of models from a config file
ALL_MODELS = tuple([("tiny_yolov3_%d" % res, res) for res in range(320, 640, 32)])

# A set of models loaded from the frontend
MODELS_IN_USE = set()


def server(frame_buffers, admin_queue, inf_ready_queue, api_results):
    # Start running the server to listen the requests from the frontend
    from server import app, init
    init(api_results, ALL_MODELS, frame_buffers, admin_queue, inf_ready_queue)
    inf_ready_queue.get()
    while True:
        app.run(debug=False, host="0.0.0.0")


def async_infer(worker):
    # Keep running prediction to process any requests in the queue
    while True:
        worker.predict_async()


class NcsWorker(object):
    def __init__(self, devid, frame_buffer, results, number_of_ncs, api_results, model_name, input_size, plugin):
        self.devid = devid
        self.model_name = 'voc_%s' % model_name  # TODO: Support generic models
        self.model_xml = "./models/FP16/%s.xml" % self.model_name
        self.model_bin = "./models/FP16/%s.bin" % self.model_name
        self.class_names = load_names(dataset='voc')  # TODO: Support generic training dataset (e.g., coco)

        self.m_input_size = input_size
        self.num_requests = 4
        self.inferred_request = [0] * self.num_requests
        self.heap_request = []
        self.inferred_cnt = 0

        self.plugin = plugin
        self.net = IENetwork(model=self.model_xml, weights=self.model_bin)
        self.input_blob = next(iter(self.net.inputs))
        self.exec_net = self.plugin.load(network=self.net, num_requests=self.num_requests)

        self.frame_buffer = frame_buffer
        self.results = results
        self.api_results = api_results
        self.number_of_ncs = number_of_ncs
        self.skip_frame = 0
        self.roop_frame = 0

    def image_preprocessing(self, color_image):
        # Resize the input color_image to the model input size and swap axis for OpenVINO
        camera_width, camera_height = color_image.shape[1], color_image.shape[0]
        scale = min(self.m_input_size / camera_width, self.m_input_size / camera_height)
        new_w, new_h = int(camera_width * scale), int(camera_height * scale)
        resized_image = cv2.resize(color_image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        canvas = np.full((self.m_input_size, self.m_input_size, 3), 128)
        top, bottom = (self.m_input_size - new_h) // 2, (self.m_input_size - new_h) // 2 + new_h
        left, right = (self.m_input_size - new_w) // 2, (self.m_input_size - new_w) // 2 + new_w
        canvas[top:bottom, left:right, :] = resized_image
        prep_img = canvas
        prep_img = prep_img[np.newaxis, :, :, :]  # Batch size axis add
        prep_img = prep_img.transpose((0, 3, 1, 2))  # NHWC to NCHW
        return prep_img

    def predict_async(self):
        try:
            if not self.frame_buffer.empty():
                self.roop_frame += 1
                if self.roop_frame <= self.skip_frame:
                    self.frame_buffer.get()
                    return
                self.roop_frame = 0
                frameId, image, t_conf, t_iou, mode = self.frame_buffer.get()

                req_num = search_list(self.inferred_request, 0)
                if req_num > -1:
                    prep_img = self.image_preprocessing(image)
                    self.exec_net.start_async(request_id=req_num, inputs={self.input_blob: prep_img})
                    self.inferred_request[req_num] = 1
                    self.inferred_cnt += 1
                    if self.inferred_cnt == sys.maxsize:
                        self.inferred_request = [0] * self.num_requests
                        self.heap_request = []
                        self.inferred_cnt = 0
                    heapq.heappush(self.heap_request, (self.inferred_cnt, req_num, frameId,
                                                       image.shape[1], image.shape[0], t_conf, t_iou, mode))

            if len(self.heap_request) > 0:
                cnt, dev, frameId, camera_width, camera_height, t_conf, t_iou, mode = heapq.heappop(self.heap_request)
                if self.exec_net.requests[dev].wait(0) == 0:
                    self.exec_net.requests[dev].wait(-1)
                    scale = min(self.m_input_size / camera_width, self.m_input_size / camera_height)
                    new_w, new_h = int(camera_width * scale), int(camera_height * scale)
                    outputs = self.exec_net.requests[dev].outputs
                    objects = YOLOv3_ParseOutput(self.net, outputs, (new_h, new_w), (camera_height, camera_width),
                                                 self.class_names, t_conf, t_iou)
                    self.api_results.put((frameId, objects, mode, t_iou))
                    self.inferred_request[dev] = 0
                else:
                    heapq.heappush(self.heap_request, (cnt, dev, frameId, camera_width, camera_height,
                                                       t_conf, t_iou, mode))
        except:
            import traceback
            traceback.print_exc()


def inferencer(results, frame_buffers, number_of_ncs, api_results, inf_ready_queue, models_in_use, sleep_time=2):
    threads = []

    for devid in range(number_of_ncs):
        print("Plugin the device in now")
        plugin = IEPlugin(device='MYRIAD')
        print('[Device %d/%d] IEPlugin initialized' % (devid + 1, number_of_ncs))

        loaded_model_count = 0
        mi, model = None, None
        for model_name in models_in_use:
            for mi in range(len(ALL_MODELS)):
                model = ALL_MODELS[mi]
                if model[0] == model_name:
                    break
            while True:
                try:
                    model_name, input_size = model
                    thworker = threading.Thread(target=async_infer, args=(
                        NcsWorker(devid, frame_buffers[mi], results, number_of_ncs, api_results[mi],
                                  model_name=model_name, input_size=input_size, plugin=plugin),
                    ))
                    thworker.start()
                    threads.append(thworker)
                    print('[Device %d/%d] %d/%d models loaded' % (devid + 1, number_of_ncs,
                                                                  loaded_model_count + 1, len(models_in_use)))
                    loaded_model_count += 1
                    break
                except RuntimeError:
                    print("Failed, trying again in %d second(s)" % sleep_time)
                    sleep(sleep_time)
        print('[Device %d/%d] Initialization finished' % (devid + 1, number_of_ncs))
    print('All devices and models are initialized. Start serving detection requests...')
    inf_ready_queue.put("")
    for th in threads:
        th.join()


if __name__ == '__main__':
    processes = []
    try:
        mp.set_start_method('forkserver')
        frame_buffers = []  # per-model input buffer
        api_results = []    # per-model output buffer

        for _ in ALL_MODELS:
            frame_buffers.append(mp.Queue(10))
            api_results.append(mp.Queue())
        results = mp.Queue()

        print("Starting streaming and inferencer")
        admin_queue = mp.Queue()
        inf_ready_queue = mp.Queue()

        # Start streaming
        p = mp.Process(target=server, args=(frame_buffers, admin_queue, inf_ready_queue, api_results), daemon=True)
        p.start()
        processes.append(p)

        # Start inferencer
        p = mp.Process(target=inferencer, args=(results, frame_buffers, number_of_ncs, api_results,
                                                inf_ready_queue, MODELS_IN_USE), daemon=True)
        p.start()
        processes.append(p)
        while True:
            models = set(admin_queue.get())
            if MODELS_IN_USE == models:
                inf_ready_queue.put("")
                continue
            while MODELS_IN_USE:
                MODELS_IN_USE.pop()
            MODELS_IN_USE.update(models)
            print("Reloading", MODELS_IN_USE)
            p.terminate()
            p = mp.Process(target=inferencer, args=(results, frame_buffers, number_of_ncs, api_results,
                                                    inf_ready_queue, MODELS_IN_USE), daemon=True)
            p.start()
            processes.append(p)
    except:
        import traceback
        traceback.print_exc()
    finally:
        for p in range(len(processes)):
            processes[p].terminate()
        print("\n\nFinished\n\n")
