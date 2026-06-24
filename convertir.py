import tensorflow as tf
import glob, os
import numpy as np

modelos = glob.glob('modelos_ml/*.keras')
print('Modelos encontrados:', modelos)

if not modelos:
    print('ERROR: No se encontró ningún modelo en modelos_ml/')
    exit()

modelo_path = modelos[-1]
modelo = tf.keras.models.load_model(modelo_path)
print('Modelo cargado OK')
print('Input shape:', modelo.input_shape)

# Crear función concreta con input shape fijo
@tf.function(input_signature=[tf.TensorSpec(shape=modelo.input_shape, dtype=tf.float32)])
def predict(x):
    return modelo(x)

concrete_func = predict.get_concrete_function()
converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func], modelo)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
tflite_model = converter.convert()

salida = modelo_path.replace('.keras', '.tflite')
with open(salida, 'wb') as f:
    f.write(tflite_model)

print('Convertido OK:', salida, f'({len(tflite_model)//1024} KB)')