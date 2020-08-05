#!/usr/bin/env python
# coding: utf-8

# In[ ]:


try:
    get_ipython().magic(u'tensorflow_version 2.x')
except Exception:
    pass
import tensorflow as tf
from tensorflow.keras.layers import Lambda
import tensorflow.keras.backend as backend
import tensorflow.keras.layers as layers
import tensorflow.keras.models as models


# In[ ]:


##### MobileNetV2
relu6 = tf.keras.layers.ReLU(6.)
def _conv_block(inputs, filters, kernel, strides):
    x = tf.keras.layers.Conv2D(filters, kernel, padding='same', strides=strides)(inputs)
    x = tf.keras.layers.BatchNormalization()(x)
    return relu6(x)
def _bottleneck(inputs, filters, kernel, t, s, r=False):
    tchannel = inputs.shape[-1] * t
    x = _conv_block(inputs, tchannel, (1, 1), (1, 1))
    x = tf.keras.layers.DepthwiseConv2D(kernel, strides=(s, s), depth_multiplier=1, padding='same')(x)
    x = tf.keras.layers.BatchNormalization()(x)
    x = relu6(x)
    x = tf.keras.layers.Conv2D(filters, (1, 1), strides=(1, 1), padding='same')(x)  # 降维，改层为瓶颈层
    x = tf.keras.layers.BatchNormalization()(x)
    if r:
        x = tf.keras.layers.add([x, inputs])
    return x

def _inverted_residual_block(inputs, filters, kernel, t, strides, n):
    x = _bottleneck(inputs, filters, kernel, t, strides)
    for i in range(1, n):
        x = _bottleneck(x, filters, kernel, t, 1, True)
    return x

def MobileNetV2(input_shape, nclasses=2):
    """
    # Arguments
        input_shape: An integer or tuple/list of 3 integers, shape
            of input tensor.
        classes: Integer, number of classes.
    # Returns
        MobileNetv2 model.
    """

    inputs = tf.keras.layers.Input(shape=input_shape, name='input')
    x = _conv_block(inputs, 32, (3, 3), strides=(2, 2))   # 0.5*size         n_layers = 1
 
    x = _inverted_residual_block(x, 16, (3, 3), t=1, strides=1, n=1)  #        n_layers = 3
    x = _inverted_residual_block(x, 24, (3, 3), t=6, strides=2, n=2)  # 0.5*size,  n_layers = 6

    x = _inverted_residual_block(x, 32, (3, 3), t=6, strides=2, n=3)  # 0.5*size,  n_layers = 9
    x = _inverted_residual_block(x, 64, (3, 3), t=6, strides=2, n=4)  # 0.5*size,  n_layers = 12
    x = _inverted_residual_block(x, 96, (3, 3), t=6, strides=1, n=3)  #        n_layers = 9
    x = _inverted_residual_block(x, 160, (3, 3), t=6, strides=2, n=3)  # 0.5*size,  n_layers = 9
    x = _inverted_residual_block(x, 320, (3, 3), t=6, strides=1, n=1)  #        n_layers = 3

    x = _conv_block(x, 1280, (1, 1), strides=(1, 1))  # n_layers = 1
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Reshape((1, 1, 1280))(x)
    x = tf.keras.layers.Dropout(0.3, name='Dropout')(x)
    x = tf.keras.layers.Conv2D(nclasses, (1, 1), padding='same')(x)  # n_layers = 1
    x = tf.keras.layers.Activation('softmax', name='final_activation')(x)
    output = tf.keras.layers.Reshape((nclasses,), name='output')(x)
    model = tf.keras.models.Model(inputs, output)
    return model


# In[ ]:


def Upsample(tensor, size_1):  
    '''bilinear upsampling'''
    y = tf.image.resize(images=tensor, size=size_1)
    return y

def ASPP_2(tensor):

    '''atrous spatial pyramid pooling'''
    dims = backend.int_shape(tensor)
    y_pool = tf.keras.layers.AveragePooling2D(pool_size=(
        dims[1], dims[2]), name='average_pooling')(tensor)
    y_pool = tf.keras.layers.Conv2D(filters=128, kernel_size=1, padding='same',
                    kernel_initializer='he_normal', name='pool_1x1conv2d', use_bias=False)(y_pool)
    y_pool = tf.keras.layers.BatchNormalization(name=f'bn_1')(y_pool)
    y_pool = tf.keras.layers.Activation('relu', name=f'relu_1')(y_pool)
    y_pool = Upsample(tensor=y_pool, size_1=[dims[1], dims[2]])
    ## 1x1 conv
    y_1 = tf.keras.layers.Conv2D(filters=128, kernel_size=1, dilation_rate=1, padding='same',
                 kernel_initializer='he_normal', name='ASPP_conv2d_d1', use_bias=False)(tensor)
    y_1 = tf.keras.layers.BatchNormalization(name=f'bn_2')(y_1)
    y_1 = tf.keras.layers.Activation('relu', name=f'relu_2')(y_1)
    ## 3x3 dilated conv
    y_6 = tf.keras.layers.Conv2D(filters=128, kernel_size=3, dilation_rate=6, padding='same',
                 kernel_initializer='he_normal', name='ASPP_conv2d_d6', use_bias=False)(tensor)
    y_6 = tf.keras.layers.BatchNormalization(name=f'bn_3')(y_6)
    y_6 = tf.keras.layers.Activation('relu', name=f'relu_3')(y_6)
    ## 3x3 dilated conv
    y_12 = tf.keras.layers.Conv2D(filters=128, kernel_size=3, dilation_rate=12, padding='same',
                  kernel_initializer='he_normal', name='ASPP_conv2d_d12', use_bias=False)(tensor)
    y_12 = tf.keras.layers.BatchNormalization(name=f'bn_4')(y_12)
    y_12 = tf.keras.layers.Activation('relu', name=f'relu_4')(y_12)
    
    ## 3x3 dilated conv
    y_18 = tf.keras.layers.Conv2D(filters=128, kernel_size=3, dilation_rate=18, padding='same',
                  kernel_initializer='he_normal', name='ASPP_conv2d_d18', use_bias=False)(tensor)
    y_18 = tf.keras.layers.BatchNormalization(name=f'bn_5')(y_18)
    y_18 = tf.keras.layers.Activation('relu', name=f'relu_5')(y_18)
    
    ## concat
    y = tf.keras.layers.concatenate([y_pool, y_1, y_6, y_12, y_18], name='ASPP_concat')
    y = tf.keras.layers.Conv2D(filters=128, kernel_size=1, dilation_rate=1, padding='same',
               kernel_initializer='he_normal', name='ASPP_conv2d_final', use_bias=False)(y)
    y = tf.keras.layers.BatchNormalization(name=f'bn_final')(y)
    y = tf.keras.layers.Activation('relu', name=f'relu_final')(y)
    return y

def DeepLabV3Plus_improve(input_shape, base_model, d_feature, m_feature, l_feature, nclasses=2):
    '''
    Arguments:
        input_shape: (img_height, img_width, img_channel)
        base_model: backbone network
        d_feature, m_feature, l_feature: features corresponding 
                    to the deep, middle, and low layers of the backbone model
        nclass: number of classes.
    '''
    print('*** Building DeepLabv3Plus Network ***')
    (img_height, img_width, img_channel) = input_shape
    ## deep features
    base_model = base_model(input_shape, nclasses)
    image_features = base_model.get_layer(index = d_feature).output
    x_a = ASPP_2(image_features) 
    x_a = Upsample(tensor=x_a, size_1=[img_height // 4, img_width // 4])  
    ## middle features (1/4 patch size)
    x_b = base_model.get_layer(index = m_feature).output
    x_b = layers.Conv2D(filters=48, kernel_size=1, padding='same',
                 kernel_initializer='he_normal', name='low_level_projection', use_bias=False)(x_b)
    x_b = layers.BatchNormalization(name=f'bn_low_level_projection')(x_b)
    x_b = layers.Activation('relu', name='low_level_activation')(x_b)
    ## middle features (1/2 patch size)
    x_c = base_model.get_layer(index = l_feature).output
    x_c = layers.Conv2D(filters=48, kernel_size=1, padding='same',
                 kernel_initializer='he_normal', name='low_level_projection_2', use_bias=False)(x_c)
    x_c = layers.BatchNormalization(name=f'bn_low_level_projection_2')(x_c)
    x_c = layers.Activation('relu', name='low_level_activation_2')(x_c)
    ## concat
    x = layers.concatenate([x_a, x_b], name='decoder_concat_1')
    
    x = layers.Conv2D(filters=128, kernel_size=3, padding='same', activation='relu',
               kernel_initializer='he_normal', name='decoder_conv2d_1', use_bias=False)(x)
    x = layers.BatchNormalization(name=f'bn_decoder_1')(x)
    x = layers.Activation('relu', name='activation_decoder_1')(x)
    x = layers.Conv2D(filters=128, kernel_size=3, padding='same', activation='relu',
               kernel_initializer='he_normal', name='decoder_conv2d_2', use_bias=False)(x)
    x = layers.BatchNormalization(name=f'bn_decoder_2')(x)
    x = layers.Activation('relu', name='activation_decoder_2')(x)
    x = Upsample(x, [img_height//2, img_width//2])
    ## concat
    x_2 = layers.concatenate([x, x_c], name='decoder_concat_3')
    x_2 = layers.Conv2DTranspose(filters=128, kernel_size=3, strides=2, padding='same', 
               kernel_initializer='he_normal', name='decoder_deconv2d', use_bias=False)(x_2)
    x_2 = layers.BatchNormalization(name=f'bn_decoder_4')(x_2)
    x_2 = layers.Activation('relu', name='activation_decoder_4')(x_2)
    last = tf.keras.layers.Conv2D(1, (1,1),
                        strides=1,
                        padding='same',
                        kernel_initializer='he_normal',
                        activation= 'sigmoid')  ## (bs, 256, 256, 1)
    x_2 = last(x_2)
    model = models.Model(inputs=base_model.input, outputs=x_2, name='DeepLabV3_Plus_improve')
    print(f'*** Output_Shape => {model.output_shape} ***')
    return model

