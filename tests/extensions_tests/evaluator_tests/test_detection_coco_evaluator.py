import numpy as np
import unittest

import chainer
from chainer.datasets import TupleDataset
from chainer.iterators import SerialIterator
from chainer import testing

from chainercv.extensions import DetectionCOCOEvaluator
from chainercv.utils import generate_random_bbox


class _DetectionStubLink(chainer.Link):

    def __init__(self, bboxes, labels):
        super(_DetectionStubLink, self).__init__()
        self.count = 0
        self.bboxes = bboxes
        self.labels = labels

    def predict(self, imgs):
        n_img = len(imgs)
        bboxes = self.bboxes[self.count:self.count + n_img]
        labels = self.labels[self.count:self.count + n_img]
        scores = [np.ones_like(l) for l in labels]

        self.count += n_img

        return bboxes, labels, scores


class TestDetectionCOCOEvaluator(unittest.TestCase):

    def setUp(self):
        bboxes = [generate_random_bbox(5, (256, 324), 24, 120)
                  for _ in range(10)]
        areas = [[np.array([(bb[2] - bb[0]) * bb[3] - bb[0]]) for bb in bbox]
                 for bbox in bboxes]
        labels = 2 * np.ones((10, 5), dtype=np.int32)
        crowdeds = np.zeros((10, 5))
        self.dataset = TupleDataset(
            np.random.uniform(size=(10, 3, 32, 48)),
            bboxes, labels, areas, crowdeds)
        self.link = _DetectionStubLink(bboxes, labels)
        self.iterator = SerialIterator(
            self.dataset, 5, repeat=False, shuffle=False)
        self.evaluator = DetectionCOCOEvaluator(
            self.iterator, self.link, label_names=('cls0', 'cls1', 'cls2'))
        self.expected_ap = 1

    def test_evaluate(self):
        reporter = chainer.Reporter()
        reporter.add_observer('target', self.link)
        with reporter:
            mean = self.evaluator.evaluate()

        # No observation is reported to the current reporter. Instead the
        # evaluator collect results in order to calculate their mean.
        self.assertEqual(len(reporter.observation), 0)

        key = 'ap/iou=0.50:0.95/area=all/maxDets=100'
        np.testing.assert_equal(
            mean['target/m{}'.format(key)], self.expected_ap)
        np.testing.assert_equal(mean['target/{}/cls0'.format(key)], np.nan)
        np.testing.assert_equal(mean['target/{}/cls1'.format(key)], np.nan)
        np.testing.assert_equal(
            mean['target/{}/cls2'.format(key)], self.expected_ap)

    def test_call(self):
        mean = self.evaluator()
        # main is used as default
        key = 'ap/iou=0.50:0.95/area=all/maxDets=100'
        np.testing.assert_equal(mean['main/m{}'.format(key)], self.expected_ap)
        np.testing.assert_equal(mean['main/{}/cls0'.format(key)], np.nan)
        np.testing.assert_equal(mean['main/{}/cls1'.format(key)], np.nan)
        np.testing.assert_equal(
            mean['main/{}/cls2'.format(key)], self.expected_ap)

    def test_evaluator_name(self):
        self.evaluator.name = 'eval'
        mean = self.evaluator()
        # name is used as a prefix

        key = 'ap/iou=0.50:0.95/area=all/maxDets=100'
        np.testing.assert_equal(
            mean['eval/main/m{}'.format(key)], self.expected_ap)
        np.testing.assert_equal(mean['eval/main/{}/cls0'.format(key)], np.nan)
        np.testing.assert_equal(mean['eval/main/{}/cls1'.format(key)], np.nan)
        np.testing.assert_equal(
            mean['eval/main/{}/cls2'.format(key)], self.expected_ap)

    def test_current_report(self):
        reporter = chainer.Reporter()
        with reporter:
            mean = self.evaluator()
        # The result is reported to the current reporter.
        self.assertEqual(reporter.observation, mean)


testing.run_module(__name__, __file__)
