import os
import sys
from models import ocr
from keras.optimizers import SGD
from keras.callbacks import LambdaCallback
import keras.backend as K
import numpy as np
from tensorflow.python import debug as tf_debug
from utils.dictnet import DictNetGenerator, DictNetDataSet
from utils.weights import WeightsDumper

image_dir = "/Users/albanseurat/Downloads/90kDICT32px/"

dictnet = DictNetDataSet(image_dir)

def decode_predict_ctc(out, top_paths=1):
    results = []
    beam_width = 5
    if beam_width < top_paths:
        beam_width = top_paths
    for i in range(top_paths):
        lables = K.get_value(K.ctc_decode(out, input_length=np.ones(out.shape[0]) * out.shape[1],
                                          greedy=False, beam_width=beam_width, top_paths=top_paths)[0][i])[0]
        text = dictnet.labels_to_text(lables)
        results.append(text)
    return results


if "debug" in sys.argv:
    sess = K.get_session()
    sess = tf_debug.LocalCLIDebugWrapperSession(sess)
    K.set_session(sess)

if "train" in sys.argv:
    ocrModel = ocr.OcrWithLoss(dictnet.lexicon_len())
    dumper = WeightsDumper(ocrModel)
    dumper.restore()

    optimizer = SGD(lr=0.02, decay=1e-6, momentum=0.9, nesterov=True, clipnorm=5)
    ocrModel.compile(loss={'ctc': lambda y_true, y_pred: y_pred}, optimizer=optimizer)

    generator = DictNetGenerator(dictnet)
    ocrModel.summary()

    ocrModel.fit_generator(generator=generator, callbacks=[
        LambdaCallback(on_batch_end=lambda batch, logs: dumper.dump())])  # , use_multiprocessing=True, workers=4)

elif "predict" in sys.argv:

    ocrModel = ocr.Ocr(dictnet.lexicon_len(), weights=None)
    dumper = WeightsDumper(ocrModel)
    dumper.restore()

    for root, dirs, files in os.walk("output"):
        files = (x for x in files if x.endswith("png"))
        for filename in files:
            img = dictnet.preprocess(filename, dir="output")
            predicted = ocrModel.predict(img)
            print(filename, decode_predict_ctc(predicted))
    
else:
    raise NotImplementedError