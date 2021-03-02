# -*- coding: utf-8 -*-
"""
/***************************************************************************
 pytorch_segmentation_models_trainer
                              -------------------
        begin                : 2021-03-02
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Philipe Borba - Cartographic Engineer
                                                            @ Brazilian Army
        email                : philipeborba at gmail dot com
 ***************************************************************************/
/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ****
"""

import hydra
from omegaconf import DictConfig
from pytorch_lightning import Trainer
from pytorch_segmentation_models_trainer.predict import predict
from pytorch_segmentation_models_trainer.train import train


@hydra.main(config_path="conf", config_name="config")
def main(cfg: DictConfig) -> Trainer:
    if cfg.mode == 'train':# or 'mode' not in cfg:
        return train(cfg)
    elif cfg.mode == 'predict':
        return predict(cfg)
    else:
        raise NotImplementedError

if __name__=="__main__":
    main()
