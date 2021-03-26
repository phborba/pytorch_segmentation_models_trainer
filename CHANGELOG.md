# Version 0.4

## Polygoniztion by Frame Field Learning features

- FrameField dataset
- FrameField Learning
- Polygonization

# Version 0.3.2

Bug fixes on image callback when Pytorch Lightning DDP is used.

# Version 0.3.1

Bug fixes when Pytorch Lightning DDP is used.

# Version 0.3.0

- Custom metric option in the model config;
- pytorch_toolbelt added as required package. This enables usage of the models, losses and metrics in the training;
- Added the option of setting a limit of rows to be read in the csv dataset;
- Added the option of setting a root_dir to the dataset. This root_dir will be concatenated to the entry in the csv dataset before loading the image;
- Bug fixes on image_callback;

# Version 0.2.1

Fixes relative path bug on dataset

# Version 0.2.0

## New custom callbacks:

- ImageSegmentationResultCallback: Callback that logs the results of the training on TensorBoard and on saved files; and
- WarmupCallback: Applies freeze weight on encoder during callback epochs and then unfreezes the weights after the warmup epochs.

## Metrics added to Segmentation Model:

- Accuracy;
- Precision;
- Recall; and
- Jaccard Index (IoU).

# Version 0.1.4

First version of metrics added.

Bug fixes on dataset reading with prefix path.

# Version 0.1.3

Bug fix on entry points and --config-dir syntax.

# Version 0.1.2

Bug fix on Python's version.

# Minor bug fix

Bug fix.

# First Release

Framework based on Pytorch, Pytorch Lightning, segmentation_models.pytorch and hydra to train semantic segmentation models using yaml config files.