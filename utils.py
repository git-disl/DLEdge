import cv2
import base64
import numpy as np
import networkx as nx


def base64tocv2(s):
    """
    Convert base64 encoded string of image to cv2 image
    :param s: base64 encoded string
    :return: cv2 image of the encoded string
    """
    return cv2.imdecode(np.fromstring(base64.decodebytes(str.encode(s.split(',')[-1])), dtype=np.uint8), 1)


def intersection_over_union(box_1, box_2):
    """
    Compute intersection over union for ensemble detection
    :param box_1: (x, y, w, h) of the first bounding box
    :param box_2: (x, y, w, h) of the second bounding box
    :return: Intersection over union
    """
    xmin_1, ymin_1 = box_1['bbox'][0], box_1['bbox'][1]
    xmin_2, ymin_2 = box_2['bbox'][0], box_2['bbox'][1]
    xmax_1, ymax_1 = box_1['bbox'][2] + xmin_1, box_1['bbox'][3] + ymin_1
    xmax_2, ymax_2 = box_2['bbox'][2] + xmin_2, box_2['bbox'][3] + ymin_2
    width_of_overlap_area = min(xmax_1, xmax_2) - max(xmin_1, xmin_2)
    height_of_overlap_area = min(ymax_1, ymax_2) - max(ymin_1, ymin_2)
    if width_of_overlap_area < 0 or height_of_overlap_area < 0:
        area_of_overlap = 0
    else:
        area_of_overlap = width_of_overlap_area * height_of_overlap_area
    box_1_area = (ymax_1 - ymin_1) * (xmax_1 - xmin_1)
    box_2_area = (ymax_2 - ymin_2) * (xmax_2 - xmin_2)
    area_of_union = box_1_area + box_2_area - area_of_overlap
    if area_of_union == 0:
        return 0
    return area_of_overlap / area_of_union


def search_list(sl, x, NOT_FOUND=-1):
    """
    A searching function to find an empty slot in the async request list
    :param sl: Search list
    :param x: Search target value
    :param NOT_FOUND: A value indicating target not found (must be less than 0 to avoid confusion)
    :return: The first index of the target value in the search list
    """
    return sl.index(x) if x in sl else NOT_FOUND


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

#-------------------------------------------------
# Helper functions for vote clique
def get_cliques(models_predictions):
    #Creat the graph
    G = nx.Graph()

    # Index of the node
    i = 0
    # Index of the model (to track model-prediction)
    j = 0

    for model in models_predictions:
        j += 1
        for object in models_predictions[model]:
            G.add_node(i, bbox=object['bbox'])
            G.nodes[i]['class'] = object['class']
            G.nodes[i]['score'] = object['score']
            G.nodes[i]['model'] = j
            i += 1

    #Now we have all the objects detected in a graph
    # Create clique for each node and save it as list
    # cliques[i] will contain a set of vertices
    cliques_aux = nx.find_cliques(G)
    cliques_aux  = list(cliques_aux)
    cliques = []
    for cl in cliques_aux:
        cliques.append({cl[0]})

    # Now we have to build the edges
    # Also store them in array to sort
    #In edges[i], first and second number are vertices
    # the third number is IoU
    edges = []
    n = len(list(G.nodes()))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            #If iou is not zero, build edge.
            # intersection_over_union expects a dictionary
            iou = intersection_over_union(G.nodes[i],G.nodes[j])
            if iou != 0:
                G.add_edge(i,j, iou = iou)
                edges.append([i,j,iou])


    # Sort the edges by weight (IoU) in descending order
    edges.sort(key = lambda x: x[2], reverse=True)

    # merge the two cliques the edges would connect if
    # their sets of vertex colors are disjoint
    for edge in edges:
        #Find the clique for each vertex
        i = -1
        j = -1
        for k in range(len(cliques)):
            #Recall: cliques[k] contains indices of vertices in that clique
            if(edge[0] in cliques[k]):
                i = k
            if(edge[1] in cliques[k]):
                j = k

        #Compute set of colors (model) for each clique
        colorsClique1 = set()
        colorsClique2 = set()
        for vertex in cliques[i]:
            color = G.nodes[vertex]['model']
            colorsClique1.add(color)

        for vertex in cliques[j]:
            color = G.nodes[vertex]['model']
            colorsClique2.add(color)

        intersection = colorsClique1.intersection(colorsClique2)
        # If disjoint of colors, merge
        if(len(intersection) == 0):
            cliques[i] = cliques[i].union(cliques[j])
            cliques.pop(j)

    # return the remaining cliques
    return cliques, G

# @param predictions: array with dictionaries. Each dictionary is a prediction,
# with the same structure as in detect_objects_response
def vote_cliques(cliques, G, voting_threshold = 0.5):
    # Counting the number of diferent models (colors) in the clique gives us
    # how many models vote for a clique
    cliqueVotes = []
    totalColors = set()
    for cl in cliques:
        colors = set()
        for node in cl:
            color = G.nodes[node]['model']
            colors.add(color)
            totalColors.add(color)
        cliqueVotes.append(len(colors))

    predictions = []
    totalColors = len(totalColors)
    for i in range(len(cliques)):
        percentVote = cliqueVotes[i] /  totalColors
        if(percentVote >= voting_threshold):
            # Cliques is an array of sets. Each set is a clique with
            # the indices of the nodes in the clique
            # Get the node (box prediction) with highest score in each clique
            prediction = {'score': -1}
            for indexNode in cliques[i]:
                box = G.nodes[indexNode]
                if(box['score'] > prediction['score']):
                    prediction = box
            predictions.append(prediction)


    return predictions

# End of helper functions for majorty voting on graph cliques
#---------------------------------------------------
