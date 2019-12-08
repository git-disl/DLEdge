def search_list(l, x, NOT_FOUND=-1):
    """
    A searching function to find an empty slot in the async request list
    :param l: Search list
    :param x: Search target value
    :param NOT_FOUND: A value indicating target not found (must be less than 0 to avoid confusion)
    :return: The first index of the target value in the search list
    """
    return l.index(x) if x in l else NOT_FOUND


def load_names(dataset):
    """
    Loading the class names from a local file
    :param dataset: The dataset that is used to train the object detector
    :return: A list of class names, index of a class name is the class id
    """
    class_names = []
    with open('./data/%s.names' % dataset, 'r') as f:
        for line in f.readlines():
            class_name = line.strip()
            if len(class_name) > 0:
                class_names.append(class_name)
    return class_names


class DetectedObject(object):
    def __init__(self, x, y, h, w, class_id, confidence, h_scale, w_scale, class_names):
        """
        DetectedObject is a class that describe an object detected by *any* detection algorithm.
        It is scaled to the input image resolution.
        :param x: x-coordinate of the top left corner
        :param y: y-coordinate of the top left corner
        :param h: Height of the bounding box
        :param w: Width of the bounding box
        :param class_id: Class id of the detected object
        :param confidence: Prediction confidence
        :param h_scale: Scaling factor to convert from model resolution to original input resolution
        :param w_scale: Scaling factor to convert from model resolution to original input resolution
        :param class_names: A list of class name with a correct ordering
        """
        self.xmin = int((x - w / 2) * w_scale)
        self.ymin = int((y - h / 2) * h_scale)
        self.xmax = int(self.xmin + w * w_scale)
        self.ymax = int(self.ymin + h * h_scale)
        self.class_id = class_id
        self.name = class_names[class_id]
        self.confidence = confidence
