# Vendored model

`face_detection_yunet_2023mar.onnx` — YuNet face detector from
[OpenCV Zoo](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet),
MIT licensed, 227 KB.

Committed rather than downloaded on first run so the tool works offline and
cannot break because an upstream URL moved.

It is used in preference to the Haar cascades because it returns the eye centres
directly and, being a small neural network rather than a texture matcher, it
still finds them behind glasses and sunglasses. On this lab's photos the Haar
eye cascades failed on 7 of 15; YuNet found eyes on all of them.
