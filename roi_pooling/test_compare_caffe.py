import unittest
import tempfile
import os
import numpy as np
import caffe
import tensorflow as tf
import numpy as np
from roi_pooling_ops import roi_pooling


def roinet_file(pooled_w, pooled_h, n_rois):
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write("""
        name: 'roi pooling net' force_backward: true
        input: 'data' input_shape {{ dim: 1 dim: 1 dim: 4 dim: 5 }}
        
        input: 'rois'
        input_shape {{
          dim: {n_rois} # to be changed on-the-fly to num ROIs
          dim: 5 # [batch ind, x1, y1, x2, y2] zero-based indexing
        }}

        layer {{
          name: "roi_pool5"
          type: "ROIPooling"
          bottom: "data"
          bottom: "rois"
          top: "output"
          roi_pooling_param {{
            pooled_w: {pooled_w}
            pooled_h: {pooled_h}
            #spatial_scale: 0.0625 # 1/16
            spatial_scale: 1 # 1/16
          }}
          }}""".format(pooled_w=pooled_w, pooled_h=pooled_h, n_rois=n_rois))
        return f.name
    
def ROI_caffe(x, rois, pooled_w, pooled_h):
    #TODO: return the gradients also
    #TODO: maybe check the initial conditions for the ROIs, input etc.?
    
    net_file = roinet_file(pooled_w=pooled_w, pooled_h=pooled_h, n_rois=len(rois))
    net = caffe.Net(net_file, caffe.TRAIN)
    os.remove(net_file)
    
    net.blobs['data'].data[...] = x
    net.blobs['rois'].data[...]  = rois
    net.forward()
    output = net.blobs['output'].data
    
    #TODO: compute the gradient 
    dummy_grad = np.zeros_like(x) #
    return output, dummy_grad

def ROI_tensorflow(x_input, rois_input, pooled_w, pooled_h):
    input = tf.placeholder(tf.float32)
    rois = tf.placeholder(tf.int32)
    
    y = roi_pooling(input, rois, pool_height=2, pool_width=2)
    mean = tf.reduce_mean(y)
    grads = tf.gradients(mean, input)
    with tf.Session('') as sess:
        y_output =  sess.run(y, feed_dict={input: x_input, rois: rois_input})
        grads_output = sess.run(grads, feed_dict={input: x_input, rois: rois_input})
    return y_output, grads_output
    
x = np.arange(20).reshape(1, 1, 4, 5)
rois = [[0, 0, 0, 1, 1],
        [0, 0, 0, 3, 3],
        [0, 2, 2, 3, 3],
        [0, 0, 0, 4, 3]]
rois = np.array(rois)
tf_y, tf_grad = ROI_tensorflow(x, rois, 2,2)
caffe_y, caffe_grad = ROI_caffe(x, rois, 2,2) 

#    def test_backward(self):
#        x = 7
#        self.net.blobs['three'].diff[...] = x
#        self.net.backward()
#        for y in self.net.blobs['data'].diff.flat:
#            self.assertEqual(y, 10**3 * x)
#
#    def test_reshape(self):
#        s = 4
#        self.net.blobs['data'].reshape(s, s, s, s)
#        self.net.forward()
#        for blob in self.net.blobs.itervalues():
#            for d in blob.data.shape:
#                self.assertEqual(s, d)
